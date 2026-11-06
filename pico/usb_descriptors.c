/**
 * SPDX-License-Identifier: GPL-3.0-only
 * @file usb_descriptors.c
 * TinyUSB descriptors for one CDC console with a stable board-specific serial.
 */
#include "tusb.h"
#include "pico/unique_id.h"
#include <string.h>

/// Development identity, matching TinyUSB's CDC example VID/PID convention.
static const tusb_desc_device_t device = {.bLength = sizeof(tusb_desc_device_t),
    .bDescriptorType = TUSB_DESC_DEVICE,
    .bcdUSB = 0x0200,
    .bDeviceClass = TUSB_CLASS_MISC,
    .bDeviceSubClass = MISC_SUBCLASS_COMMON,
    .bDeviceProtocol = MISC_PROTOCOL_IAD,
    .bMaxPacketSize0 = 64,
    .idVendor = 0xcafe,
    .idProduct = 0x4001,
    .bcdDevice = 0x0100,
    .iManufacturer = 1,
    .iProduct = 2,
    .iSerialNumber = 3,
    .bNumConfigurations = 1};
/// TinyUSB requires these callback names and owns the lifetime of returned data.
const uint8_t *tud_descriptor_device_cb(void) {
    return (const uint8_t *)&device;
}
enum { ITF_CDC, ITF_CDC_DATA, ITF_COUNT };
static const uint8_t configuration[] = {
    TUD_CONFIG_DESCRIPTOR(
        1, ITF_COUNT, 0, TUD_CONFIG_DESC_LEN + TUD_CDC_DESC_LEN, 0, 100),
    TUD_CDC_DESCRIPTOR(ITF_CDC, 4, 0x81, 8, 0x02, 0x82, 64)};
const uint8_t *tud_descriptor_configuration_cb(uint8_t index) {
    /// There is only one configuration, containing CDC control and data interfaces.
    (void)index;
    return configuration;
}

const uint16_t *tud_descriptor_string_cb(uint8_t index, uint16_t language) {
    (void)language;
    static uint16_t descriptor[64];
    static char serial[PICO_UNIQUE_BOARD_ID_SIZE_BYTES * 2 + 1];
    const char *s;
    if (index == 0) {
        descriptor[0] = (TUSB_DESC_STRING << 8) | 4;
        descriptor[1] = 0x0409;
        return descriptor;
    }
    /// Keep strings in ASCII here; USB string descriptors below expand to UTF-16LE.
    switch (index) {
        case 1:
            s = "6502 Board Project";
            break;
        case 2:
            s = "6502 USB Terminal";
            break;
        case 3:
            pico_get_unique_board_id_string(serial, sizeof(serial));
            s = serial;
            break;
        case 4:
            s = "Board console";
            break;
        default:
            return NULL;
    }
    size_t length = strlen(s);
    if (length > 63) {
        length = 63;
    }
    for (size_t i = 0; i < length; i++) {
        descriptor[i + 1] = (uint8_t)s[i];
    }
    /// The first word packs descriptor type and total byte length, including itself.
    descriptor[0] = (uint16_t)((TUSB_DESC_STRING << 8) | (2 * length + 2));
    return descriptor;
}
