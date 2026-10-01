个人比较习惯用 IDEA 读源码。下面把一套「可改、可调试、不影响日常 JDK」的 JDK 8 源码阅读环境搭起来。

截图按步骤放在同目录 `assets/` 下，文件名与正文引用一致；没有图时先按文字操作即可。

## 创建项目

用 IDEA 新建一个普通 Java 项目，作为源码阅读工程。示例代码可勾掉，空项目即可。

![](assets/01-new-project.png)

创建完成后大致如下：

![](assets/02-project-created.png)

## 下载 JDK 8

到 Oracle 官网下载 **JDK 8** 的安装包 / 压缩包（需登录；没有账号先注册）。

![](assets/03-oracle-jdk8.png)

![](assets/04-jdk8-download-list.png)

![](assets/05-login-download.png)

![](assets/06-download-progress.png)

## 解压源码

解压下载的 JDK 包。为方便区分，可以把目录重命名成例如 `jdk1.8.0_xxx-src-read`。

![](assets/07-unzip-jdk.png)

![](assets/08-rename-jdk-dir.png)

进入 JDK 安装目录，找到 `src.zip`——主要 Java 源码在这里。

![](assets/09-src-zip.png)

把 `src.zip` 复制到刚建好的 IDEA 项目目录下，解压。解压完成后删掉项目里的这份 `src.zip`，只保留解压出的源码树（通常就是项目下的 `src`）。

![](assets/10-copy-src-zip.png)

![](assets/11-unzip-to-project.png)

![](assets/12-delete-src-zip.png)

## 配置 Project Structure

目标：给这份阅读工程挂一个**独立的 JDK**，避免改源码时污染日常使用的 JDK。

打开 **File → Project Structure**（或快捷键），新增一个 JDK：

![](assets/13-project-structure.png)

![](assets/14-add-jdk.png)

把新建的 SDK 重命名，例如 `JDK8-SourceRead`，和日常 JDK 区分开。

![](assets/15-rename-sdk.png)

在该 SDK 的 **Sourcepath** 里：

1. 移除原先指向安装目录自带源码的那条 Sourcepath  
2. 改成指向项目里解压出来的源码目录（项目下的 `src`）

![](assets/16-remove-default-sourcepath.png)

![](assets/17-choose-project-src.png)

![](assets/18-sourcepath-done.png)

![](assets/19-sourcepath-confirm.png)

再给这个 SDK 加上 `tools.jar`（JDK 8 的 `lib/tools.jar`）。不加的话，编译/阅读部分工具类时容易报找不到类。

![](assets/20-add-tools-jar.png)

![](assets/21-select-tools-jar.png)

![](assets/22-tools-jar-added.png)

![](assets/23-sdk-classpath.png)

最后把**当前项目的 Project SDK** 改成刚配好的这份 JDK。

![](assets/24-project-sdk.png)

## 配置编译器

在 IDEA 的编译器设置里，适当加大堆内存，源码工程体积不小，默认内存偶发吃紧。

![](assets/25-compiler-heap.png)

## 配置调试器

取消 IDEA 调试时对 JDK 内部代码的限制，否则 Step Into 进不去源码。

路径大致是：**Settings → Build, Execution, Deployment → Debugger**，关掉类似 *Do not step into the Java Runtime Classes* / *Do not step into the classes...* 这类限制（具体文案随 IDEA 版本略有差异）。

![](assets/26-debugger-step-into.png)

## 补齐找不到的两个类

配置完成后，若提示缺少 `sun.font.FontConfigManager`、`sun.awt.UNIXToolkit`，在项目源码树里补两个包：`sun.font`、`sun.awt`，并从 OpenJDK 8u 对应路径拷源码进来。

先建包：

![](assets/27-create-packages.png)

`FontConfigManager`：

- [hg.openjdk.org …/sun/font/FontConfigManager.java](https://hg.openjdk.org/jdk8u/jdk8u/jdk/file/7fcf35286d52/src/solaris/classes/sun/font/FontConfigManager.java)

![](assets/28-fontconfigmanager-web.png)

![](assets/29-fontconfigmanager-ide.png)

`UNIXToolkit`：

- [hg.openjdk.org …/sun/awt/UNIXToolkit.java](https://hg.openjdk.org/jdk8u/jdk8u/jdk/file/7fcf35286d52/src/solaris/classes/sun/awt/UNIXToolkit.java)

![](assets/30-unixtoolkit-web.png)

![](assets/31-unixtoolkit-ide.png)

这两个类在 Oracle 发行的 `src.zip` 里常被裁掉或平台相关，Linux / Solaris 侧实现在 OpenJDK 的 `src/solaris/classes` 下。

## 编译测试

随便编译/运行一下，确认环境无异常：

![](assets/32-compile-ok.png)

之后就可以在调试里 Step Into，边读源码边记笔记：

![](assets/33-debug-into-source.png)

## Reference

1. [https://www.cnblogs.com/kukuxjx/p/17218492.html](https://www.cnblogs.com/kukuxjx/p/17218492.html)
2. [https://hg.openjdk.org/jdk8u/jdk8u/jdk/file/7fcf35286d52/src/solaris/classes/sun](https://hg.openjdk.org/jdk8u/jdk8u/jdk/file/7fcf35286d52/src/solaris/classes/sun)
