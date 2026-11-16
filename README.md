# ELRS Baro RX — 带气压计的 DIY ExpressLRS 接收机

基于 [ExpressLRS](https://github.com/ExpressLRS/ExpressLRS) **3.6.4** 的定制接收机固件，运行在 **ESP32-C3** 上，集成 **SPL06-001 气压计**（高度/升降速度遥测）与 **MAVLink** 输出，支持 PWM 舵机直出。

> 硬件设计一并开源，见 [`hardware/EDA/`](hardware/EDA/README.md)。

## 项目定位

这是一个"20 元级 ELRS 接收机"的完整实现：C3 开发板 + E28 2.4G 射频模块 + 气压计 + 排针，**一个分立元器件都不用焊**，全部用模块堆叠。适合固定翼、滑翔机等需要高度遥测的机型。

## 功能特性

| 功能 | 说明 |
|---|---|
| **ELRS 2.4GHz 接收** | SX1280（E28-2G4M12S）模块，CRSF 协议，支持 50~500Hz 刷新率 |
| **气压计遥测** | SPL06-001，自动探测 `0x76`/`0x77` 双地址，输出相对高度 + 升降速度（CRSF `BARO_ALTITUDE` 帧 `0x09`） |
| **MAVLink 输出** | 集成 `c_library_v2`，可向飞控/地面站输出 MAVLink 消息 |
| **PWM 直出** | 最多 6 通道 PWM 舵机输出，无需飞控 |
| **电池电压采集** | ADC 分压（10K/1K），CRSF 电池遥测 |
| **WiFi 配置** | 上电自动开启热点，`10.0.0.1` 网页配置（可改引脚映射、烧写固件） |

## 硬件

| 部件 | 型号 | 说明 |
|---|---|---|
| 主控 | ESP32-C3-Zero / Supermini | RISC-V 160MHz，内置 WiFi/BLE |
| 射频 | E28-2G4M12S（SX1280） | 2.4GHz，SPI 接口 |
| 气压计 | SPL06-001 | I2C，高精度气压/温度 |
| 接口 | 3× 6Pin 排针（IPCP254M06PB08V） | PWM 输出 / 电源 |

### 引脚定义

来自 `hardware/RX/Generic C3 2400 PWM Baro.json`：

| 功能 | GPIO |
|---|---|
| 射频 SPI（MISO / MOSI / SCK / NSS） | 5 / 4 / 6 / 7 |
| 射频 BUSY / DIO1 / RST | 3 / 1 / 2 |
| 气压计 I2C（SDA / SCL） | 21 / 20 |
| RGB LED | 8（GRB 顺序） |
| PWM 输出（4 路） | 9 / 10 / 18 / 19 |
| 电池电压 ADC | GPIO3（R10 10K / R9 1K 分压，scale 909） |

完整原理图与 PCB 见 [`hardware/EDA/`](hardware/EDA/README.md)。

## 编译

需要 [PlatformIO](https://platformio.org/)（VSCode 插件或 CLI）。

```bash
# Arduino 框架
pio run -e Unified_ESP32C3_2400_RX_via_UART

# 出厂固件（打包 bootloader 等）
pio run -e Unified_ESP32C3_2400_RX_via_UART -t build
```

产物位于 `.pio/build/Unified_ESP32C3_2400_RX_via_UART/firmware.bin`。

### 烧写

- **UART**：USB 转串口接 GPIO21(TX)/GPIO20(RX)，按住 BOOT 上电进入下载模式
- **WiFi**：接收机上电后连热点 `ExpressLRS RX`，浏览器打开 `10.0.0.1`，在网页中上传 `firmware.bin`
- **Betaflight Passthrough**：通过飞控串口透传烧写

### 目标选择

首次烧写后在 WiFi 配置页（`10.0.0.1/hardware.html`）选择目标：
**`Generic C3 2400 PWM Baro`** —— 这是本硬件对应的 target。选错会导致引脚不匹配。

## 快速上手

1. 烧写固件，进入 `10.0.0.1` 确认 target 为 `Generic C3 2400 PWM Baro`
2. 与遥控器对频（ELRS 标准 binding 流程）
3. 在遥控器 LUA 脚本中检查：
   - 各通道方向是否正确
   - 遥测页是否出现 **高度 / 升降速度**（气压计工作正常）
   - 电池电压读数是否与实际相符（不符则调 `vbat_scale`）
4. 若气压计无读数：检查 I2C 接线（SDA=21 / SCL=20），确认模块供电 3.3V

## 目录结构

```
├── hardware/
│   ├── EDA/                     # 嘉立创 EDA 原理图/PCB 备份与预览
│   └── RX/Generic C3 2400 PWM Baro.json   # 本硬件的引脚定义
├── lib/
│   ├── Baro/                    # SPL06 / BMP280 气压计驱动 + 遥测发布
│   ├── c_library_v2/            # MAVLink C 库（MIT）
│   └── ...                      # ELRS 原生各模块
├── src/                         # 主程序
├── targets/                     # PlatformIO 编译目标
└── user_defines.txt             # 用户自定义编译宏
```

## 气压计实现要点

- **驱动**：`lib/Baro/baro_spl06.cpp`，双地址探测（`0x76` / `0x77`），CHIP_ID `0x10`
- **过采样**：气压 32×（约 53ms）、温度 8×（约 15ms），结果移位使能
- **标定**：读取 18 字节出厂系数 `c0/c1/c00/c10/c01/c11/c20/c21/c30`，二次温度补偿
- **高度**：国际标准大气公式 `4433000 × (1 − (P/P₀)^0.1903)`，输出厘米
- **遥测**：`lib/Baro/devBaro.cpp` 发布 CRSF `BARO_ALTITUDE`（0x09）；首帧作为"家"基准，之后输出相对高度与 4 点平滑的垂直速度

## 相关文档

- [`hardware/EDA/README.md`](hardware/EDA/README.md) — 硬件设计说明与引脚表
- [`history_202608181622.md`](history_202608181622.md) — 开发过程记录

## 致谢与许可

- 上游项目：[ExpressLRS](https://github.com/ExpressLRS/ExpressLRS)（GPLv3）
- 硬件原始设计：坚持不用舵 / ServolessWaverider（"20 元 ELRS"）
- 气压计版本改造：LZY
- MAVLink 库：[mavlink/c_library_v2](https://github.com/mavlink/c_library_v2)（MIT）

本项目同样以 **GPLv3** 发布，详见 [`LICENSE`](LICENSE)。
