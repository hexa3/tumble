/* STM32G041J6M6 register-level drivers.  Reference: RM0444 (STM32G0x1 reference manual) and the
 * STM32G041x6/x8 datasheet.  Pin bonding is from KiCad's STM32G041J6Mx symbol.  Alternate-function
 * numbers, the ADC channel and the I2C timing word are as I read those documents; confirm each in
 * STM32CubeMX before bring-up (listed in docs/v2/BRINGUP.md).
 *
 * One-time setup over SWD: option byte NRST_MODE = 2 (GPIO), otherwise pin 4 is a reset input and
 * the UART cannot use it. */
#include "hw.h"
#include "stm32g0xx.h"

volatile uint32_t hw_ms;
void SysTick_Handler(void) { hw_ms++; }

void hw_delay_ms(uint32_t ms)
{
    uint32_t t = hw_ms;
    while (hw_ms - t < ms) __WFI();
}

static void delay_us(uint32_t us) { for (volatile uint32_t i = 0; i < us * 16; i++) {} }

/* ------------------------------------------------------------------ clocks: HSI16 -> PLL 64 MHz */
static void clocks(void)
{
    FLASH->ACR = (FLASH->ACR & ~FLASH_ACR_LATENCY) | FLASH_ACR_LATENCY_1 | FLASH_ACR_PRFTEN;  /* 2 WS */
    RCC->PLLCFGR = RCC_PLLCFGR_PLLSRC_HSI | (8u << RCC_PLLCFGR_PLLN_Pos) | RCC_PLLCFGR_PLLREN |
                   (1u << RCC_PLLCFGR_PLLR_Pos);                 /* 16 / 1 * 8 / 2 = 64 MHz */
    RCC->CR |= RCC_CR_PLLON;
    while (!(RCC->CR & RCC_CR_PLLRDY)) {}
    RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW) | (2u << RCC_CFGR_SW_Pos);
    while ((RCC->CFGR & RCC_CFGR_SWS) != (2u << RCC_CFGR_SWS_Pos)) {}
    /* I2C1 and RNG from HSI16 so their timing does not depend on the PLL */
    RCC->CCIPR = (RCC->CCIPR & ~(RCC_CCIPR_I2C1SEL | RCC_CCIPR_RNGSEL)) |
                 (2u << RCC_CCIPR_I2C1SEL_Pos) | (1u << RCC_CCIPR_RNGSEL_Pos);
    RCC->IOPENR |= RCC_IOPENR_GPIOAEN | RCC_IOPENR_GPIOBEN;
    RCC->APBENR1 |= RCC_APBENR1_I2C1EN | RCC_APBENR1_USART2EN | RCC_APBENR1_PWREN;
    RCC->APBENR2 |= RCC_APBENR2_ADCEN | RCC_APBENR2_SYSCFGEN;
    RCC->AHBENR |= RCC_AHBENR_RNGEN;
    SysTick_Config(64000);                                       /* 1 kHz */
}

/* ------------------------------------------------------------------ GPIO */
enum { IN = 0, OUT = 1, AF = 2, ANALOG = 3 };

static void pin(GPIO_TypeDef *g, int n, int mode, int af, int pull, int od)
{
    g->MODER = (g->MODER & ~(3u << (2 * n))) | ((uint32_t)mode << (2 * n));
    g->PUPDR = (g->PUPDR & ~(3u << (2 * n))) | ((uint32_t)pull << (2 * n));
    g->OTYPER = (g->OTYPER & ~(1u << n)) | ((uint32_t)od << n);
    if (mode == AF) {
        volatile uint32_t *afr = &g->AFR[n >> 3];
        *afr = (*afr & ~(15u << (4 * (n & 7)))) | ((uint32_t)af << (4 * (n & 7)));
    }
}

static void gpio(void)
{
    /* every GPIO bonded to a pin we use, other than the one we use, stays analog (high-Z) */
    pin(GPIOB, 7, ANALOG, 0, 0, 0);            /* pin 1: NOISE_ADC */
    pin(GPIOA, 2, AF, 1, 1, 0);                /* pin 4: USART2_TX, half-duplex, pull-up */
    pin(GPIOA, 9, AF, 6, 0, 1);                /* pin 5: I2C1_SCL (external 4.7k pull-ups) */
    pin(GPIOA, 10, AF, 6, 0, 1);               /* pin 6: I2C1_SDA */
}

void hw_release_swd(void)
{
    GPIOA->BRR = 1u << 13;
    pin(GPIOA, 13, OUT, 0, 0, 0);              /* pin 7: NOISE_EN, low */
    pin(GPIOA, 14, ANALOG, 0, 0, 0);           /* pin 8: SWCLK off ... */
    pin(GPIOB, 5, IN, 0, 2, 0);                /* ... ACC_INT1 on PB5, pull-down (LIS3DH INT1 is active high) */
    EXTI->EXTICR[1] = (EXTI->EXTICR[1] & ~0xFF00u) | (0x01u << 8);   /* EXTI5 <- port B */
    EXTI->RTSR1 |= 1u << 5;
    EXTI->IMR1 |= 1u << 5;
    NVIC_EnableIRQ(EXTI4_15_IRQn);
}
void EXTI4_15_IRQHandler(void) { EXTI->RPR1 = 1u << 5; }

void hw_noise(int on) { if (on) GPIOA->BSRR = 1u << 13; else GPIOA->BRR = 1u << 13; }
int hw_acc_int(void) { return (GPIOB->IDR >> 5) & 1; }
int hw_usb_present(void) { return (GPIOA->IDR >> 2) & 1; }

/* ------------------------------------------------------------------ USART2, single wire, 115200 */
static void uart_init(void)
{
    USART2->CR1 = 0;
    USART2->BRR = 64000000u / 115200u;
    USART2->CR3 = USART_CR3_HDSEL;
    USART2->CR1 = USART_CR1_TE | USART_CR1_RE | USART_CR1_UE;
}

int hw_uart_getc(void)
{
    if (USART2->ISR & USART_ISR_ORE) USART2->ICR = USART_ICR_ORECF;
    return (USART2->ISR & USART_ISR_RXNE_RXFNE) ? (int)(USART2->RDR & 0xFF) : -1;
}

void hw_uart_puts(const char *s)
{
    while (*s) {
        while (!(USART2->ISR & USART_ISR_TXE_TXFNF)) {}
        USART2->TDR = (uint8_t)*s++;
    }
    while (!(USART2->ISR & USART_ISR_TC)) {}
}

/* ------------------------------------------------------------------ I2C1, 400 kHz from HSI16 */
#define I2C_TIMEOUT 40000

static int wait(uint32_t mask)
{
    for (uint32_t t = 0; t < I2C_TIMEOUT; t++) {
        if (I2C1->ISR & I2C_ISR_NACKF) { I2C1->ICR = I2C_ICR_NACKCF | I2C_ICR_STOPCF; return -1; }
        if (I2C1->ISR & mask) return 0;
    }
    return -2;
}

static int i2c_write(void *ctx, uint8_t addr, const uint8_t *buf, size_t n)
{
    (void)ctx;
    if (n > 255) return -3;
    I2C1->CR2 = ((uint32_t)addr << 1) | ((uint32_t)n << I2C_CR2_NBYTES_Pos) | I2C_CR2_AUTOEND | I2C_CR2_START;
    for (size_t i = 0; i < n; i++) {
        if (wait(I2C_ISR_TXIS)) return -1;
        I2C1->TXDR = buf[i];
    }
    if (wait(I2C_ISR_STOPF)) return -1;
    I2C1->ICR = I2C_ICR_STOPCF;
    return 0;
}

static int i2c_read(void *ctx, uint8_t addr, uint8_t reg, uint8_t *buf, size_t n)
{
    (void)ctx;
    I2C1->CR2 = ((uint32_t)addr << 1) | (1u << I2C_CR2_NBYTES_Pos) | I2C_CR2_START;
    if (wait(I2C_ISR_TXIS)) return -1;
    I2C1->TXDR = reg;
    if (wait(I2C_ISR_TC)) return -1;
    I2C1->CR2 = ((uint32_t)addr << 1) | ((uint32_t)n << I2C_CR2_NBYTES_Pos) | I2C_CR2_RD_WRN |
                I2C_CR2_AUTOEND | I2C_CR2_START;
    for (size_t i = 0; i < n; i++) {
        if (wait(I2C_ISR_RXNE)) return -1;
        buf[i] = (uint8_t)I2C1->RXDR;
    }
    if (wait(I2C_ISR_STOPF)) return -1;
    I2C1->ICR = I2C_ICR_STOPCF;
    return 0;
}

static void i2c_delay(void *ctx, uint32_t ms) { (void)ctx; hw_delay_ms(ms); }
const i2c_bus_t hw_i2c = {i2c_write, i2c_read, i2c_delay, 0};

static void i2c_init(void)
{
    I2C1->CR1 = 0;
    I2C1->TIMINGR = 0x10320309;     /* 16 MHz I2CCLK, Fast-mode 400 kHz (reference-manual timing example) */
    I2C1->CR1 = I2C_CR1_PE;
}

/* ------------------------------------------------------------------ ADC: PB7 = ADC1_IN11 */
static void adc_init(void)
{
    ADC1->CFGR2 = (1u << ADC_CFGR2_CKMODE_Pos);                  /* PCLK / 2 */
    ADC1->CR |= ADC_CR_ADVREGEN;
    delay_us(30);
    ADC1->CR |= ADC_CR_ADCAL;
    while (ADC1->CR & ADC_CR_ADCAL) {}
    ADC1->ISR = ADC_ISR_ADRDY;
    ADC1->CR |= ADC_CR_ADEN;
    while (!(ADC1->ISR & ADC_ISR_ADRDY)) {}
    ADC1->SMPR = 1u;                                             /* 3.5 cycles: fast samples of the noise */
    ADC1->CHSELR = 1u << 11;
}

void hw_noise_samples(uint16_t *buf, size_t n)
{
    for (size_t i = 0; i < n; i++) {
        ADC1->CR |= ADC_CR_ADSTART;
        while (!(ADC1->ISR & ADC_ISR_EOC)) {}
        buf[i] = (uint16_t)ADC1->DR;
    }
}

/* ------------------------------------------------------------------ RNG (HSI16) */
void hw_trng(uint32_t *w, size_t n)
{
    RNG->CR |= RNG_CR_RNGEN;
    for (size_t i = 0; i < n; i++) {
        while (!(RNG->SR & RNG_SR_DRDY)) {
            if (RNG->SR & (RNG_SR_SEIS | RNG_SR_CEIS)) {
                RNG->SR = 0;
                RNG->CR &= ~RNG_CR_RNGEN;
                RNG->CR |= RNG_CR_RNGEN;
            }
        }
        w[i] = RNG->DR;
    }
}

/* ------------------------------------------------------------------ sleep */
void hw_sleep(void)
{
    hw_noise(0);
    SysTick->CTRL &= ~SysTick_CTRL_ENABLE_Msk;
    PWR->CR1 = (PWR->CR1 & ~PWR_CR1_LPMS) | PWR_CR1_LPMS_0;        /* Stop 1 */
    SCB->SCR |= SCB_SCR_SLEEPDEEP_Msk;
    EXTI->RPR1 = 1u << 5;
    if (!hw_acc_int()) __WFI();
    SCB->SCR &= ~SCB_SCR_SLEEPDEEP_Msk;
    clocks();                                                      /* Stop wakes on HSI16 */
}

void hw_init(void)
{
    clocks();
    gpio();
    uart_init();
    i2c_init();
    adc_init();
}
