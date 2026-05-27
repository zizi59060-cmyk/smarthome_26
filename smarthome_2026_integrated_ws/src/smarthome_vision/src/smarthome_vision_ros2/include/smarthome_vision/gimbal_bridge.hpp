#pragma once

#include <cstdint>
#include <string>
#include <vector>

#include "smarthome_vision/protocol.hpp"

namespace smarthome_vision
{

class GimbalBridge
{
public:
  GimbalBridge(const std::string & device, int baudrate);
  ~GimbalBridge();

  bool isOpened() const;

  bool sendTarget(uint8_t mode, bool tracking, uint8_t class_id, float x, float y, float z);

  bool updateReceive();
  uint8_t getMode() const;

  // 新增：构造将要发给下位机的十六进制字符串
  std::string buildTargetPacketHex(
    uint8_t mode, bool tracking, uint8_t class_id, float x, float y, float z) const;

private:
  bool openPort();
  void closePort();
  bool parseModePacket();

private:
  int fd_ = -1;
  std::string device_;
  int baudrate_ = 115200;

  uint8_t current_mode_ = static_cast<uint8_t>(VisionMode::IDLE);
  std::vector<uint8_t> rx_buffer_;
};

}  // namespace smarthome_vision