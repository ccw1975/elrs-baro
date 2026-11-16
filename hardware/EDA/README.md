# 硬件设计文件（嘉立创 EDA 专业版）

本目录包含 DIY ELRS 接收机（SPL06 气压计版）的硬件设计资料。

## 文件说明

| 文件 | 内容 |
|---|---|
| `ELRS接收机_嘉立创EDA备份.epro2` | 嘉立创 EDA 专业版工程备份（原理图 + PCB，可直接导入恢复） |
| `schematic_c3zero_baro.webp` | 原理图：ESP32-C3-Zero + E28 2.4G 射频模块 + SPL06-001 气压计 + 6Pin 排针 ×3 + ADC 分压 |
| `schematic_supermini.webp` | 原理图：ESP32-C3 Supermini 版（参考，连接关系用于 hardware.html 配置） |
| `PCB_top.webp` / `PCB_bottom.webp` | PCB 正/反面预览 |

## 恢复工程

1. 打开嘉立创 EDA 专业版 → 文件 → 导入 → EasyEDA 备份（.epro2）
2. 选择本目录的 `.epro2` 文件即可还原原理图与 PCB

## 关键引脚（与固件 targets/DIY_C3_2400_PWM_BARO.ini 对应）

| 功能 | 引脚 |
|---|---|
| E28 射频（SPI） | MISO/MOSI/SCK/NSS/BUSY/DIO1/RST |
| SPL06 气压计（I2C） | SDA/SCL（GPIO20/21） |
| SPL06 复位 | RST（GPIO10） |
| ADC 电池电压采集 | GPIO3（R10 10K / R9 1K 分压） |
| PWM 输出 CH1~CH6 | 6Pin 排针 ×3（信号 / +5V / GND） |

## 版本

- 板子：Board2（V1.1，优化了 RF 净空区和供电线宽），更新日期 2026-08-25
- 作者：LZY / 坚持不用舵（ServolessWaverider）
