/* STM32G041J6 (SO-8) hardware layer.  Six I/O pins:
 *   pin 1  PB7   NOISE_ADC (ADC1_IN11)        pin 5  PA9   I2C1_SCL
 *   pin 4  PA2   UART (USART2_TX, half-duplex) pin 6  PA10  I2C1_SDA
 *   pin 7  PA13  SWDIO, then NOISE_EN         pin 8  PA14/PB5  SWCLK, then ACC_INT1 (PB5, EXTI5)
 * hw_init() leaves pins 7 and 8 as SWD; hw_release_swd() (called 2 s after reset) takes them over. */
#ifndef HW_H
#define HW_H
#include <stddef.h>
#include <stdint.h>
#include "i2c_bus.h"

extern const i2c_bus_t hw_i2c;
extern volatile uint32_t hw_ms;

void hw_init(void);
void hw_release_swd(void);
void hw_noise(int on);
void hw_noise_samples(uint16_t *buf, size_t n);
void hw_trng(uint32_t *w, size_t n);
int hw_usb_present(void);           /* the bridge holds the UART line high only while USB is plugged in */
int hw_uart_getc(void);             /* -1 if nothing */
void hw_uart_puts(const char *s);
int hw_acc_int(void);
void hw_sleep(void);                /* STOP1 until the accelerometer interrupt */
void hw_delay_ms(uint32_t ms);
#endif
