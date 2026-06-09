#pragma once

#include <cstdint>

namespace smarthome_vision
{

enum class VisionMode : uint8_t
{
  IDLE = 0,
  DETECT_OBJECT = 1,
  DETECT_QR = 2
};

struct __attribute__((packed)) GimbalToVision
{
  uint8_t head[2] = {'V', 'S'};
  uint8_t mode = static_cast<uint8_t>(VisionMode::IDLE);
  uint16_t crc16 = 0;
};

struct __attribute__((packed)) VisionToGimbal
{
  uint8_t head[2] = {'S', 'P'};
  uint8_t command = 0;
  int8_t class_id = -1;
  uint8_t zone_id = 0;
  float x = 0.0f;
  float y = 0.0f;
  float z = 0.0f;
  float vx = 0.0f;
  float vy = 0.0f;
  float wz = 0.0f;
  uint16_t crc16 = 0;
};

}  // namespace smarthome_vision
