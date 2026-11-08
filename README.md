# GPU Check

> 已并入 [System Check](https://github.com/xiongnemo/ios-system-check)（它的 GPU 页），以后在那边更新；这个仓库不再更新。

一个把 iOS 游戏可能用到的图形能力逐项测一遍的小应用：每一项单独测，各自给出 PASS / FAIL / SKIP，
以及让应用崩掉或卡住的那一项的 CRASHED / HUNG，每项一行说明。打开就按顺序全部跑完，不用点；
“Run again” 从头再跑一遍。

最早是为了测 Redmi K40（alioth）上的 iOS 16.5 移植而写的：那里的 OpenGL ES 是 Mesa 的 freedreno（Adreno 650），
外面套着移植自己的 EAGLContext，没有 Metal。普通 iPhone 上它就是一个普通应用。

- OpenGL ES 1、2、3 的上下文：能不能建，GL_VENDOR / RENDERER / VERSION / 着色语言版本、最大纹理尺寸等上限、
  压缩纹理格式、全部扩展；同一个 sharegroup 的第二个上下文能不能看见第一个的纹理
- 离屏绘制（ES1 用 OES_framebuffer_object 和固定管线，ES2 用 `#version 100`，ES3 再加 `#version 300 es`）：
  64×64 的 RGBA8 帧缓冲，深度 DEPTH_COMPONENT16 或 DEPTH24_STENCIL8（顺带测模板），清屏、画三角形、glReadPixels
  读回中心和角落；深度测试、50% 混合
- 纹理格式（ES2）：RGBA8、565、4444、5551、LUMINANCE、ALPHA、LUMINANCE_ALPHA、BGRA、半浮点、浮点、非 2 的幂、
  mipmap、最大尺寸；压缩格式 PVRTC 4/2bpp、ETC1、ETC2/EAC（ES3）、ASTC 4×4、S3TC DXT1/DXT5——压缩数据在程序里
  直接拼出来（纯色块），画到 32×32 的帧缓冲里读回比较颜色。没有对应扩展的格式记为 SKIP，但照样上传一次、报出 GL 错误，
  因为游戏就是不检查扩展直接调用的
- GL 功能：渲染到纹理、VAO、glMapBufferOES / glMapBufferRange、实例化绘制、MRT、遮挡查询、fence（APPLE_sync / ES3）、
  glFinish 耗时、深度纹理、framebuffer fetch（gl_LastFragData）、导数、discard / invalidate；每一项结束时还要求
  glGetError 是干净的
- 上屏（CAEAGLLayer，RGBA8，不保留内容）：ES1/2/3 各 30 帧红绿蓝轮换并测每秒帧数、presentRenderbuffer:atTime: 和
  afterMinimumDuration:、最后一帧读回；ES2 / ES3 的 4×MSAA；present 前丢弃深度、present 后丢弃颜色和深度
  （Minecraft 每帧都这么做）。最后一幅画面（四个象限：左上红、右上绿、左下蓝、右下白）在屏幕上停 1.5 秒，留给截图
- GLKit：GLKViewController + GLKView、GLKView 截图、GLKBaseEffect、GLKTextureLoader（同步和异步，PNG 用
  UIGraphicsImageRenderer 现画）
- CADisplayLink：preferredFramesPerSecond 0 / 60 / 120 和 preferredFrameRateRange 120，各测一秒
- Core Image（EAGL、软件、默认上下文）、Metal（设备、计算着色器）、SceneKit（指定 OpenGL ES 2、默认）、SpriteKit。
  这几项在没有 Metal 的系统上最可能把应用带崩，所以排在最后

- 包名：`com.anzupop.com.ios.gpucheck`
- 最低 iOS 15.0，iPhone，竖屏
- 只用 Objective-C 和系统框架，一个 `main.m`，没有 storyboard、asset catalog
- 图标由 `mkicon.py` 生成（纯 Python）

## 崩溃和卡死

每一项开始前，应用先往 `Documents/gpucheck.log` 写一行 “running”（并 fsync），结束时写结果。
崩溃时（信号或未捕获的异常）处理函数在退出前再写一行是哪个信号。下次打开时，上次停在 “running” 的那一项就是元凶：
有信号记录的记为 CRASHED，否则（被杀掉了）记为 HUNG；它被标记下来，以后都跳过，测试从下一项接着跑。
另有一个看门狗线程：一项跑了 8 秒还没结束，就当场写下 HUNG（主线程已经卡住，应用自己救不回来，需要把它杀掉再开）。
标记一直保留，直到点 “Run again”。

## 远程读结果

每个结果同时写到 `/dev/console`（以 `gpucheck: ` 开头，每行不超过约 270 字节，长的列表分成几行）和 NSLog：

```
gpucheck: start <版本> <机型> <iOS 版本>
gpucheck: ctx.es2 + GL_RENDERER <...>
gpucheck: ctx.es2 PASS <GL_RENDERER> | <GL_VERSION> | <N> extensions, max texture <N>
gpucheck: tex.pvrtc4.rgb SKIP no GL_IMG_texture_compression_pvrtc (tried anyway: FAIL glCompressedTexImage2D ...: <GL 错误>)
gpucheck: done <N> pass, <N> fail, <N> crashed, <N> hung, <N> skipped (83 tests, <秒数> s)
```

`ID STATUS 说明` 是结果，`ID + ...` 是附带的信息（扩展列表等）。上屏的几项开始显示最后一幅画面时会打一行
“on screen now for 1.5 s: ...”。`Info.plist` 打开了文件共享，日志也可以从 Documents 里取。

## 编译

产物是 `build/GPUCheck.ipa`，没有苹果签名，只适合不校验签名的系统，比如上面那个移植，或者自己重新签名后安装。

```sh
./build.sh                                                   # macOS，用 Xcode
CC=xnu-clang SDK=$THEOS/sdks/iPhoneOS16.5.sdk ./build.sh     # Linux / WSL，需要能链接 iOS 的 clang + ld64
```

主程序直接链接 OpenGLES.framework（K40 移植只给主程序加载了 OpenGLES 的应用提供 GPU 的 OpenGL ES），
Metal、SpriteKit、SceneKit 是弱链接的：缺了哪个，应用照样能启动，对应的测试会说明。
`Entitlements.plist` 是空的：有 `ldid` 时用它做一个不带任何授权的 ad-hoc 签名。

每次推送 GitHub Actions 都会在 macOS 上编一次（也可以手动运行 `build`），IPA 作为运行的产物保存。

## 许可

MIT，见 `LICENSE`。

## 文件

| 文件 | 作用 |
|---|---|
| `main.m` | 整个应用（各项测试、崩溃记录和看门狗、表格） |
| `Info.plist` | 包名、版本、图标、文件共享 |
| `Entitlements.plist` | 用 `ldid` 签名时用的授权（空） |
| `mkicon.py` | 生成 60×60 @2x / @3x 图标 |
| `build.sh` | 编译并打包成 IPA |
