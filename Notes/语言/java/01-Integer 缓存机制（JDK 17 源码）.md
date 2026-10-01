---
title: "Integer 缓存机制（JDK 17 源码）"
date: 2026-10-01
draft: false
description: "Integer 的缓存不是业务层优化，而是 JLS 对自动装箱对象同一性 的硬要求：一定范围内的 int 装箱后必须是同一个 Integer 实例。实现落在私有静态内部类 Integer.IntegerCache，对外入口是 Integer…"
categories: ["语言"]
tags: ["语言"]
---
`Integer` 的缓存不是业务层优化，而是 **JLS 对自动装箱对象同一性** 的硬要求：一定范围内的 `int` 装箱后必须是**同一个** `Integer` 实例。实现落在私有静态内部类 `Integer.IntegerCache`，对外入口是 `Integer.valueOf(int)`。下文依据 JDK 17 的 `java.lang.Integer` 源码展开。

## 类上的 ValueBased

JDK 17 的 `Integer` 声明为：

```java
@jdk.internal.ValueBased
public final class Integer extends Number
        implements Comparable<Integer>, Constable, ConstantDesc {
```

`@ValueBased` 提醒：这类对象更宜按**值**使用。缓存让小整数在引用层面也「碰巧」同一，但业务比较仍应以 `equals` / 拆箱后的 `int` 为准，不要把 `==` 当成通用相等判断。

## 自动装箱实际调用 valueOf

编译器对 `Integer a = 10;` 这类赋值会插入 `Integer.valueOf(10)`，不会走已废弃的构造器。完整验证如下（覆盖缓存边界、`new`、`equals`、抬高上界）：

```java
public class IntegerCacheVerify {
    public static void main(String[] args) {
        Integer a = 10;                 // 编译为 Integer.valueOf(10)
        Integer b = 10;
        Integer c = Integer.valueOf(10);
        System.out.println("a == b (10): " + (a == b));
        System.out.println("a == c (10): " + (a == c));

        Integer d = 127;
        Integer e = 127;
        System.out.println("127 == : " + (d == e));

        Integer f = 128;
        Integer g = 128;
        System.out.println("128 == : " + (f == g));
        System.out.println("128 equals : " + (f.equals(g)));

        Integer h = -128;
        Integer i = -128;
        System.out.println("-128 == : " + (h == i));

        Integer j = -129;
        Integer k = -129;
        System.out.println("-129 == : " + (j == k));

        @SuppressWarnings("removal")
        Integer n = new Integer(10);
        System.out.println("new(10) == valueOf(10): " + (n == Integer.valueOf(10)));

        Integer p = 1000;
        Integer q = 1000;
        System.out.println("1000 == : " + (p == q));
    }
}
```

默认参数运行：

```bash
javac IntegerCacheVerify.java
java IntegerCacheVerify
```

输出：

```text
a == b (10): true
a == c (10): true
127 == : true
128 == : false
128 equals : true
-128 == : true
-129 == : false
new(10) == valueOf(10): false
1000 == : false
```

抬高缓存上界后再跑同一程序：

```bash
java -XX:AutoBoxCacheMax=1000 IntegerCacheVerify
```

输出：

```text
a == b (10): true
a == c (10): true
127 == : true
128 == : true
128 equals : true
-128 == : true
-129 == : false
new(10) == valueOf(10): false
1000 == : true
```

对照结论：

| 表达式 | 默认 | `AutoBoxCacheMax=1000` | 原因 |
|--------|------|------------------------|------|
| `10` / `127` / `-128` 的 `==` | `true` | `true` | 落在默认 `[low, high]=[-128, 127]` |
| `128` / `1000` 的 `==` | `false` | `true` | 默认超出 `high`；抬高后命中缓存 |
| `-129` 的 `==` | `false` | `false` | `low` 写死为 `-128`，下界抬不了 |
| `new Integer(10) == valueOf(10)` | `false` | `false` | 构造器总是新对象 |
| `128` 的 `equals` | `true` | `true` | `equals` 比值，不依赖缓存 |
## IntegerCache 类注释

`valueOf(int)` 上方、`IntegerCache` 定义前的注释：

```java
/**
 * Cache to support the object identity semantics of autoboxing for values between
 * -128 and 127 (inclusive) as required by JLS.
 *
 * The cache is initialized on first usage.  The size of the cache
 * may be controlled by the {@code -XX:AutoBoxCacheMax=<size>} option.
 * During VM initialization, java.lang.Integer.IntegerCache.high property
 * may be set and saved in the private system properties in the
 * jdk.internal.misc.VM class.
 *
 * WARNING: The cache is archived with CDS and reloaded from the shared
 * archive at runtime. The archived cache (Integer[]) and Integer objects
 * reside in the closed archive heap regions. Care should be taken when
 * changing the implementation and the cache array should not be assigned
 * with new Integer object(s) after initialization.
 */
```

拆开看：

| 要点 | 含义 |
|------|------|
| JLS | [-128, 127] 装箱必须具备对象同一性 |
| 首次使用初始化 | 静态块在类首次用到时执行 |
| `-XX:AutoBoxCacheMax` | 可抬高缓存上界 |
| `IntegerCache.high` 属性 | VM 初始化时写入 `jdk.internal.misc.VM` 的私有系统属性 |
| CDS WARNING | 缓存可随 CDS 归档；初始化后不要再往数组里塞新的 `Integer` |

静态块末尾还有断言注释：`range [-128, 127] must be interned (JLS7 5.1.7)`。

## IntegerCache 静态初始化

```java
private static class IntegerCache {
    static final int low = -128;
    static final int high;
    static final Integer[] cache;
    static Integer[] archivedCache;

    static {
        // high value may be configured by property
        int h = 127;
        String integerCacheHighPropValue =
            VM.getSavedProperty("java.lang.Integer.IntegerCache.high");
        if (integerCacheHighPropValue != null) {
            try {
                h = Math.max(parseInt(integerCacheHighPropValue), 127);
                // Maximum array size is Integer.MAX_VALUE
                h = Math.min(h, Integer.MAX_VALUE - (-low) -1);
            } catch( NumberFormatException nfe) {
                // If the property cannot be parsed into an int, ignore it.
            }
        }
        high = h;

        // Load IntegerCache.archivedCache from archive, if possible
        CDS.initializeFromArchive(IntegerCache.class);
        int size = (high - low) + 1;

        // Use the archived cache if it exists and is large enough
        if (archivedCache == null || size > archivedCache.length) {
            Integer[] c = new Integer[size];
            int j = low;
            for(int i = 0; i < c.length; i++) {
                c[i] = new Integer(j++);
            }
            archivedCache = c;
        }
        cache = archivedCache;
        // range [-128, 127] must be interned (JLS7 5.1.7)
        assert IntegerCache.high >= 127;
    }

    private IntegerCache() {}
}
```

### low / high

- `low`：**写死** `-128`，没有对应的「AutoBoxCacheMin」
- `high`：默认 `127`；若属性存在，则  
  `h = max(解析值, 127)`，再  
  `h = min(h, Integer.MAX_VALUE - (-low) - 1)`  
  保证数组长度 `(high - low) + 1` 不超过 `Integer.MAX_VALUE`

因此：

- 上界可以抬高（例如 `AutoBoxCacheMax=1000` → `high` 至少到 1000）
- 上界**不能**通过该属性降到 127 以下（`Math.max(..., 127)`）
- 下界永远是 -128，所以 `-129 == -129` 在引用意义上仍是 `false`

### 属性从哪来

注释写明：VM 启动时可能把 `-XX:AutoBoxCacheMax` 转成  
`java.lang.Integer.IntegerCache.high`，存进 `jdk.internal.misc.VM` 的 saved properties；  
静态块用 `VM.getSavedProperty(...)` 读取，而不是普通 `System.getProperty`。

属性解析失败（`NumberFormatException`）时直接忽略，退回默认 `127`。

### CDS 与 archivedCache

流程是：

1. 先定好 `high`
2. `CDS.initializeFromArchive(IntegerCache.class)` 尝试从共享归档恢复 `archivedCache`
3. 若归档不存在，或归档长度 `< size`（当前配置需要更大缓存），则现场 `new Integer[size]` 并填充
4. `cache = archivedCache`：对外只读用的就是这份数组

「归档不够大就重建」解释了：抬高 `AutoBoxCacheMax` 后，可能用不上旧归档里那份较小的 `Integer[]`。

WARNING 的含义也清楚了：归档堆区域里的 `Integer` 实例初始化后不应再被替换；`cache` 指向的数组槽位在静态块结束后视为只读。

### 填充时为何仍用 new Integer

循环里是 `c[i] = new Integer(j++)`。  
这里是**构建缓存本身**，不能再调 `valueOf`，否则会在 `IntegerCache` 尚未就绪时回头依赖缓存。

同文件里 `parseInt` 也有类似警告：

```java
/*
 * WARNING: This method may be invoked early during VM initialization
 * before IntegerCache is initialized. Care must be taken to not use
 * the valueOf method.
 */
```

VM 极早阶段只能用基本类型路径，不能碰依赖缓存的 `valueOf`。

## valueOf(int)

```java
/**
 * Returns an {@code Integer} instance representing the specified
 * {@code int} value.  If a new {@code Integer} instance is not
 * required, this method should generally be used in preference to
 * the constructor {@link #Integer(int)}, as this method is likely
 * to yield significantly better space and time performance by
 * caching frequently requested values.
 *
 * This method will always cache values in the range -128 to 127,
 * inclusive, and may cache other values outside of this range.
 *
 * @param  i an {@code int} value.
 * @return an {@code Integer} instance representing {@code i}.
 * @since  1.5
 */
@IntrinsicCandidate
public static Integer valueOf(int i) {
    if (i >= IntegerCache.low && i <= IntegerCache.high)
        return IntegerCache.cache[i + (-IntegerCache.low)];
    return new Integer(i);
}
```

### 命中与未命中

| 条件 | 行为 |
|------|------|
| `low <= i <= high` | 返回 `cache[i - low]`（写法是 `i + (-low)`） |
| 否则 | `new Integer(i)`，每次新对象 |

默认 `low = -128` 时下标：

| 值 | 下标 |
|----|------|
| -128 | 0 |
| 0 | 128 |
| 127 | 255 |
| 128 | 超出，走 `new` |

文档句 **always cache [-128, 127]，may cache other values** 与 `high` 可配置完全一致。

### @IntrinsicCandidate

注解定义在 `jdk.internal.vm.annotation.IntrinsicCandidate`：

> indicates that an annotated method may be (but is not guaranteed to be) intrinsified by the HotSpot VM. A method is intrinsified if the HotSpot VM replaces the annotated method with hand-written assembly and/or hand-written compiler IR

要点：

- HotSpot **可能**用手工汇编 / IR 替换该方法
- **不保证**一定 intrinsify，与平台和 VM 配置有关
- 改库方法语义时，VM 侧 intrinsic 必须同步
- 应用代码可忽略该注解；语义仍以 Java 源码为准

`valueOf(int)` 标了它，说明这是热点路径；读源码仍按上面的 `if` 理解即可。

## 构造器：为何不该 new Integer

```java
@Deprecated(since="9", forRemoval = true)
public Integer(int value) {
    this.value = value;
}
```

- `since="9"`，`forRemoval = true`：JDK 17 里仍可用，但已标明将删除
- **总是新对象**，不进缓存
- 所以 `new Integer(10) == Integer.valueOf(10)` 为 `false`

缓存初始化循环里仍调用该构造器，是 JDK 内部建池的特例；业务代码应只用 `valueOf` 或自动装箱。

## equals：比的是值

```java
public boolean equals(Object obj) {
    if (obj instanceof Integer) {
        return value == ((Integer)obj).intValue();
    }
    return false;
}
```

`equals` 只比包装的 `int`，与是否同一缓存实例无关。前文示例里默认配置下 `128 ==` 为 `false`，而 `128 equals` 为 `true`，就是这个原因。

## valueOf(String) 也会进缓存

```java
public static Integer valueOf(String s) throws NumberFormatException {
    return Integer.valueOf(parseInt(s, 10));
}
```

先 `parseInt` 得到 `int`，再走 `valueOf(int)`，因此 `"10"` 同样可能命中缓存。  
`parseInt` 本身返回的是基本类型，不涉及 `Integer` 同一性。

## 其它包装类缓存（对照）

同一套 JDK 17 源码里：

| 类型 | 缓存范围（实现） | 上界是否可配 |
|------|------------------|--------------|
| `Byte.valueOf` | 全部 byte（[-128, 127]） | 否 |
| `Short.valueOf` | [-128, 127] | 否（源码写死） |
| `Integer.valueOf` | 至少 [-128, 127]，`high` 可抬高 | 是（`AutoBoxCacheMax`） |
| `Long.valueOf` | [-128, 127] | 否（源码写死） |
| `Character.valueOf` | `'\u0000'`～`'\u007F'` | 否 |
| `Boolean` | `TRUE` / `FALSE` 两个常量 | — |
| `Float` / `Double` | 无同类小值缓存池 | — |

`Long` / `Short` 的 Javadoc 也写了 “may cache other values”，但 **JDK 17 源码里区间是写死的**；真正能通过 VM 选项拉高的是 `Integer`。

对照源码时可看 `$JAVA_HOME/lib/src.zip` 中的 `java.base/java/lang/Integer.java`，重点是 `IntegerCache` 静态块与 `valueOf(int)`。
