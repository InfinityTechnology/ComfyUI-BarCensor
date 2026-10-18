# ComfyUI-BarCensor

用纯色 Bar（黑/白/自定义色）代替马赛克打码。仿照 [ComfyUI-Mosaic](https://github.com/1038lab/ComfyUI-Mosaic) 的接口方式（`image + 可选 mask → image + mask + info`）。

## 节点：BarCensor

分类：`🧪AILab/▬BarCensor`

### 核心规则

1. **平行性**：Bar #1 决定整组 Bar 的角度；其余 Bar 全部由 Bar #1 沿其法线方向等距平移生成，     
   平行性是构造上保证的，不会因逐个拟合产生角度漂移。（实测：多条 Bar 的角度 spread = 0.000°）
2. **角度自动获取**（`angle_mode`）：
   - `auto_rect`（默认，推荐）：对 mask 求**最小外接矩形**（cv2.minAreaRect），取其**长边**相对 0° 的旋转角，       
     Bar 就按这个角度铺。实测矩形 mask 在 0 / 25 / -40 / 60° 下识别误差 < 0.1°。       
     角度直接由矩形的四个角点算出，不依赖 OpenCV 各版本 minAreaRect 的角度约定。
   - `auto_pca`：mask 协方差矩阵主特征向量方向（长轴）。
   - `horizontal` / `vertical` / `diagonal_down` / `diagonal_up` / `manual`。
3. **条相对主轴的朝向**（`bar_orientation`）— 决定条是顺着、还是垂直、还是相对主轴偏一点：
   - `along_axis`（默认）：条**顺着**主轴延伸。       
     宽遮罩（如双眼区域）→ 水平条 ✓；但**竖长遮罩（如站立人像）会变成竖直条**。
   - `across_axis`：条**垂直**于主轴（+90°）。**竖长区域想要水平条就选这个**，       
     也是最常需要切换的一项。
   - `axis_plus_offset`：主轴 + `axis_offset` 度，用于微调/风格化。       
     三者都会把结果归一化到 [-90°, 90°)，且整组条共用这一个角度，平行性不变。
4. **条厚自动联动**（`thickness_mode`）：
   - `auto`（默认）：`条厚 = 间距 × thickness_ratio`，其中 `间距 = 遮挡块高度 / bar_count`。       
     只要改 `bar_count`，条厚自动等比缩放，遮挡块整体尺寸不变。       
     例：block 高 98px、ratio 0.8 → 3 条 = 26.5px，5 条 = 15.7px，8 条 = 9.8px。
   - `manual`：固定 px（`bar_thickness`），仅受 `间距 × thickness_ratio` 上限约束。
5. **形状**：默认 `rectangle` —— Bar 是标准旋转矩形，直边直角；mask 只决定遮挡块的位置 / 角度 / 大小，     
   不裁形状。想要贴 mask 轮廓的弧形效果才用 `conform_mask`。

### 参数

| 参数                    | 说明                                                                                     |
| --------------------- | -------------------------------------------------------------------------------------- |
| `bar_count`           | Bar 数量。=1 时整块矩形填充；>1 时等距排布多条平行矩形 Bar，条厚自动缩放                                            |
| `angle_mode`          | auto_rect（默认）/ auto_pca / horizontal / vertical / diagonal_down / diagonal_up / manual |
| `angle`               | manual 模式下的角度（度，0=水平，90=垂直）                                                            |
| `bar_orientation`     | along_axis（顺主轴，默认）/ across_axis（垂直主轴 +90°）/ axis_plus_offset（主轴 + 偏移）                  |
| `axis_offset`         | axis_plus_offset 模式下的偏移角度（度）                                                           |
| `bar_shape`           | `rectangle`（直边矩形，默认）/ `conform_mask`（跟随 mask 轮廓）                                       |
| `thickness_mode`      | `auto`（跟随条数自动缩放，默认）/ `manual`（固定 px）                                                   |
| `thickness_ratio`     | auto：条厚 / 间距；manual：条厚上限 / 间距。默认 0.8                                                   |
| `bar_thickness`       | manual 模式下的固定条厚（px）                                                                    |
| `length_mode`         | fit_region（长度取区域旋转外接框，默认）/ full_image（贯穿全图）                                            |
| `length_overflow`     | Bar 两端向外延伸的 px                                                                         |
| `color`               | black / white / gray / custom                                                          |
| `custom_color`        | color=custom 时的十六进制色值，如 `#1a1a1a`                                                      |
| `opacity` / `feather` | 不透明度 / 边缘羽化（0=硬边，1≈抗锯齿）                                                                |
| `mask`（可选）            | 打码区域；不接 mask 则对整图铺条                                                                    |
| `invert_mask`         | 反选 mask                                                                                |
| `region_expand`       | rectangle 模式 = 遮挡块四周外扩 px；conform_mask 模式 = mask 膨胀 px                                 |

### 输出

- `image`：打码后图像
- `censor_mask`：Bar 本身的 mask（可用于后续 inpaint 等）
- `info`：字符串，回显本次实际用到的角度来源 / 角度值 / 条数 / 遮挡块尺寸 / 间距 / 条厚，方便调参

### 提示

- 做视频别用 auto 角度，逐帧估计会抖；固定镜头用 `manual` 或 `horizontal` 更稳。
- 竖长遮罩（人像/柱形区域）默认会给出竖条，想要横条把 `bar_orientation` 切到 `across_axis`。
