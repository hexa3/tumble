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

void hw_init(void)
{
    clocks();
    gpio();
}
