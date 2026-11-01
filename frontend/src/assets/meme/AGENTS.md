# Meme 素材维护

- 原始动画保存在 `originals/`，不修改源文件；顶层仅放处理后的同名 WebP，避免同一动画同时存在 GIF 和 WebP 而重复轮换。
- 使用 `frontend/scripts/process-memes.py`（Python 3 标准库 + ImageMagick），从仓库根目录运行：

  ```sh
  # 已有透明背景：只做统一裁切、缩放、对齐和格式转换
  python frontend/scripts/process-memes.py frontend/src/assets/meme/originals/reimu-fumo-spin.gif
  # 不透明背景：检查素材后显式指定背景色和容差
  python frontend/scripts/process-memes.py frontend/src/assets/meme/originals/yuyuko-fumo-spin.gif --background '#000000' --fuzz 6
  ```

- 脚本保留原始 delay，按整段动画的共同前景边界等比缩放至最大 184×184，再放入 200×200 透明画布，底部留 8px；输出循环动态 WebP，并校验画布、alpha 和总时长。相邻相同帧可能被编码器合并。
- 替换源图后重新检查背景，不沿用旧文件的抠图参数。透明源图不去背景；不透明源图从边缘去背景，不能全局删除角色上的相近颜色。保留原有水印。
- 脚本无法判断角色是否被误删。生成后在站点深色背景上查看首帧、中间帧和末帧，确认无误删、裁断或跳动，再运行 `npm --prefix frontend run build`。无法干净去背景时保留原图并说明问题，不用生成式重绘替代原动作。
- 脚本回归：`python -m unittest discover -s test/update/scripts -p test_process_memes.py -v`。
