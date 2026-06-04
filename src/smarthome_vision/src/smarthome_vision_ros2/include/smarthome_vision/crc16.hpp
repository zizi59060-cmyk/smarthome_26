#pragma once

#include <cstdint>

namespace smarthome_vision
{

uint16_t crc16_modbus(const uint8_t * data, uint32_t len);

}  // namespace smarthome_vision