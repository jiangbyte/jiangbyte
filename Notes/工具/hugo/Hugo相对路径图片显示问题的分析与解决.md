---
date: 2026-10-01
description: "写博客的时候用 Obsidian 插了张图："
categories: ["工具"]
tags: ["工具"]
---

## 先说问题

写博客的时候用 Obsidian 插了张图：

```markdown
![img](assets/example.jpg)
```

编辑器里看着好好的，一跑 `hugo` 部署上去，图裂了。打开浏览器开发者工具一看，图片请求的路径根本就不对。

检查了一圈，发现这个问题只出现在 **非 bundle 的 md 文件** 上，用目录包起来的 `index.md` 反倒没事。

## 为什么会有这个问题

### Hugo 的两种页面

Hugo 里写文章有两种姿势：

1. **Page Bundle** — 建个文件夹，里面放 `index.md`，图片丢同目录下
```
content/posts/my-post/
├── index.md
└── some-image.jpg
```

2. **Leaf Page** — 直接一个 `.md` 文件
```
content/posts/my-post.md
```

我这边的目录结构是这样的：

```
content/posts/
├── _index.md
├── assets/
│   └── example.jpg
├── my-post.md              ← 出问题的
└── my-bundle-post/
    └── index.md            ← 没问题的
```

Blowfish 主题自带的图片渲染逻辑，会先用 `$.Page.Resources.GetMatch` 去捞图片。Bundle 页面自然能捞到，但 leaf page 压根没有 page resources，捞了个空。最后 fallback 到直接把原始相对路径当 src 输出——这就是问题的起点。

### Permalink 让路径更深了一層

我的 permalink 配的是：

```yaml
permalinks:
  posts: /posts/:year/:month/:day/:slug/
```

假设文件是 `content/posts/my-post.md`，生成的页面 URL 是 `/posts/2026/06/05/my-post/`。

Leaf page 里的 `![img](assets/example.jpg)`，浏览器会以页面 URL 为基准去解析：

```
页面地址: /posts/2026/06/05/my-post/
浏览器请求: /posts/2026/06/05/my-post/assets/example.jpg   ← 404
```

但图片实际在哪？在 `content/posts/assets/example.jpg`。Hugo 构建的时候会把 content 目录下的非内容文件也发布出去，所以这张图实际是：

```
public/posts/assets/example.jpg
```

问题就是：**leaf page 在 URL 里多了好几层目录，但图片的相对路径没跟着变**。

## 怎么修的

### 方案一：改成 Page Bundle（最推荐）

最省事的做法就是把 leaf page 改成 bundle：

```
# 改之前
content/posts/my-post.md
content/posts/assets/example.jpg

# 改之后
content/posts/my-post/index.md
content/posts/my-post/assets/example.jpg
```

这样 `$.Page.Resources.GetMatch` 能找到图片，而且 Blowfish 的 responsive 图片优化也会生效。缺点是每个文章都要建目录，已有的存量文章多了有点折腾。

### 方案二：写个 render hook 兜底（我用的方案）

参考了 [Joker 的文章](https://www.joker.cc/posts/hugo-image.html/)，但里面用的 `../` 补丁只适合单层目录，我的 permalink 太深了不管用。改成了拼绝对路径。

在 `layouts/_default/_markup/render-image.html` 里覆写了 Blowfish 的图片渲染逻辑：

```go
{{- if not $isRemote -}}
  {{- $isPageBundle := eq $.Page.File.LogicalName "index.md" -}}
  {{- if $isPageBundle -}}
    {{- /* bundle: 原样走主题的逻辑 */ -}}
    {{- $resource = or ($.Page.Resources.GetMatch $urlStr) (resources.Get $urlStr) -}}
  {{- else if not (strings.HasPrefix $urlStr "/") -}}
    {{- /* leaf page + 相对路径: 用 .File.Dir 拼出正确路径 */ -}}
    {{- $correctPath := path.Join $.Page.File.Dir $urlStr -}}
    {{- $resource = or ($.Page.Resources.GetMatch $correctPath) (resources.Get $correctPath) -}}
    {{- if not $resource -}}
      {{- $urlStr = printf "/%s" $correctPath -}}
    {{- end -}}
  {{- else -}}
    {{- $resource = or ($.Page.Resources.GetMatch $urlStr) (resources.Get $urlStr) -}}
  {{- end -}}
{{- end -}}
```

核心逻辑就几件事：

1. 先判断是不是 bundle（看 `LogicalName` 是不是 `"index.md"`）
2. 不是 bundle，而且图片路径是相对路径——就用 `.Page.File.Dir` 拼出内容目录下的绝对路径
3. 试着找一下图片资源，找不到就直接用绝对路径当 src

`path.Join "posts/" "assets/example.jpg"` → `posts/assets/example.jpg` → `/posts/assets/example.jpg`

这样不管 permalink 多深，路径都不会偏。

### 验证

修之前：

```html
<img src="/posts/2026/06/05/my-post/assets/example.jpg">
<!-- 404 -->
```

修之后：

```html
<img src="/posts/assets/example.jpg">
<!-- 200 -->
```

实际效果：

![花火](assets/花火.jpg)

这张图就是 leaf page 引的，能正常显示说明修好了。

## 几个需要注意的

- **参考文章的方案不适用于深层 permalink**：他直接在相对路径前面加 `../`，只退一层。本项目的 `/:year/:month/:day/:slug/` 叠了四层，必须用绝对路径
- **Leaf page 没有图片优化**：Page bundle 的图片会被 Blowfish 做 responsive resize（生成多尺寸 + srcset），leaf page 的图不会。如果对图片体积有要求，还是推荐 bundle
- **我这修复只动了 render hook**：不影响 bundle 页面，不影响远程图片，不影响已经用了绝对路径的图片

## 总结

| 维度 | Page Bundle | Leaf Page + render hook |
|------|------------|------------------------|
| 图片优化 | ✅ responsive + srcset | ⚠️ 原图直出 |
| 改造成本 | 每篇都要建目录 | 配置一次，存量文章自动修 |
| 适合场景 | 新文章 | 已有大量 leaf page 或者共享 assets 目录 |

新文章我建议直接用 bundle。如果你跟我一样有一堆存量 leaf page 不想动，render hook 兜底一把梭也挺香的。

## 附完整 render-image.html

```go
{{- define "RenderImageSimple" -}}
  {{- $imgObj := .imgObj -}}
  {{- $src := .src -}}
  {{- $alt := .alt -}}
  <img
    class="my-0 rounded-md"
    loading="lazy"
    decoding="async"
    fetchpriority="low"
    alt="{{ $alt }}"
    src="{{ $src }}"
    {{ with $imgObj -}}
      {{ with $imgObj.Width }}width="{{ . }}"{{ end }}
      {{ with $imgObj.Height }}height="{{ . }}"{{ end }}
    {{- end }}>
{{- end -}}

{{- define "RenderImageResponsive" -}}
  {{/* Responsive Image
    The current setting sizes="(min-width: 768px) 50vw, 65vw" makes the iPhone 16 and 16 Pro
    select a smaller image, while the iPhone 16 Pro Max selects a larger image.

    Steps:
    1. Check the media queries in the `sizes` property.
    2. Find the first matching value. For example, on a mobile device with a CSS pixel width
    of 390px and DPR = 3 (iPhone 13), given setting sizes="(min-width: 768px) 50vw, 100vw",
    it matches the `100vw` option.
    3. Calculate the optimal image size: 390 × 3 × 100% (100vw) = 1170.
    4. Find the corresponding match in the `srcset`.

    To make the browser select a smaller image on mobile devices
    override the template and change the `sizes` property to "(min-width: 768px) 50vw, 30vw"

    The sizes="auto" is valid only when loading="lazy".
  */}}
  {{- $imgObj := .imgObj -}}
  {{- $alt := .alt -}}
  {{- $originalWidth := $imgObj.Width -}}

  {{- $img800 := $imgObj -}}
  {{- $img1280 := $imgObj -}}
  {{- if gt $originalWidth 800 -}}
    {{- $img800 = $imgObj.Resize "800x" -}}
  {{- end -}}
  {{- if gt $originalWidth 1280 -}}
    {{- $img1280 = $imgObj.Resize "1280x" -}}
  {{- end -}}

  {{- $srcset := printf "%s 800w, %s 1280w" $img800.RelPermalink $img1280.RelPermalink -}}


  <img
    class="my-0 rounded-md"
    loading="lazy"
    decoding="async"
    fetchpriority="auto"
    alt="{{ $alt }}"
    {{ with $imgObj.Width }}width="{{ . }}"{{ end }}
    {{ with $imgObj.Height }}height="{{ . }}"{{ end }}
    src="{{ $img800.RelPermalink }}"
    srcset="{{ $srcset }}"
    sizes="(min-width: 768px) 50vw, 65vw"
    data-zoom-src="{{ $imgObj.RelPermalink }}">
{{- end -}}

{{- define "RenderImageCaption" -}}
  {{- with .caption -}}
    <figcaption>{{ . | markdownify }}</figcaption>
  {{- end -}}
{{- end -}}

{{- $disableImageOptimizationMD := .Page.Site.Params.disableImageOptimizationMD | default false -}}
{{- $urlStr := .Destination | safeURL -}}
{{- $url := urls.Parse $urlStr -}}
{{- $altText := .Text -}}
{{- $caption := .Title -}}
{{- $isRemote := findRE "^(https?|data)" $url.Scheme -}}
{{- $resource := "" -}}

{{- if not $isRemote -}}
  {{- /* Check if this is a page bundle (index.md) or a regular leaf page */ -}}
  {{- $isPageBundle := eq $.Page.File.LogicalName "index.md" -}}
  {{- if $isPageBundle -}}
    {{- /* Page bundle: resolve images as page resources (original behavior) */ -}}
    {{- $resource = or ($.Page.Resources.GetMatch $urlStr) (resources.Get $urlStr) -}}
  {{- else if not (strings.HasPrefix $urlStr "/") -}}
    {{- /* Leaf page with relative path: resolve relative to content file directory */ -}}
    {{- $correctPath := path.Join $.Page.File.Dir $urlStr -}}
    {{- $resource = or ($.Page.Resources.GetMatch $correctPath) (resources.Get $correctPath) -}}
    {{- if not $resource -}}
      {{- /* Use absolute URL - Hugo publishes non-content files preserving content dir structure */ -}}
      {{- $urlStr = printf "/%s" $correctPath -}}
    {{- end -}}
  {{- else -}}
    {{- /* Absolute path: try page resources first, then global resources */ -}}
    {{- $resource = or ($.Page.Resources.GetMatch $urlStr) (resources.Get $urlStr) -}}
  {{- end -}}
{{- end -}}


<figure
  {{- range $k, $v := .Attributes -}}
    {{- if $v -}}
      {{- printf " %s=%q" $k ($v | transform.HTMLEscape) | safeHTMLAttr -}}
    {{- end -}}
  {{- end -}}>
  {{- if $isRemote -}}
    {{- template "RenderImageSimple" (dict "imgObj" "" "src" $urlStr "alt" $altText) -}}
  {{- else if $resource -}}
    {{- $isSVG := eq $resource.MediaType.SubType "svg" -}}
    {{- $shouldOptimize := and (not $disableImageOptimizationMD) (not $isSVG) -}}
    {{- if $shouldOptimize -}}
      {{- template "RenderImageResponsive" (dict "imgObj" $resource "alt" $altText) -}}
    {{- else -}}
      {{/* Not optimize image
        If it is an SVG file, pass the permalink
        Otherwise, pass the resource to allow width and height attributes
      */}}
      {{- if $isSVG -}}
        {{- template "RenderImageSimple" (dict "imgObj" "" "src" $resource.RelPermalink "alt" $altText) -}}
      {{- else -}}
        {{- template "RenderImageSimple" (dict "imgObj" $resource "src" $resource.RelPermalink "alt" $altText) -}}
      {{- end -}}
    {{- end -}}
  {{- else -}}
    {{- template "RenderImageSimple" (dict "imgObj" "" "src" $urlStr "alt" $altText) -}}
  {{- end -}}

  {{- template "RenderImageCaption" (dict "caption" $caption) -}}
</figure>

```