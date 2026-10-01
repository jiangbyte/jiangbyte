`java.lang.Object` 是 Java 类型体系的根：除它自身外，每个类（含数组类型）最终都继承它，因而它定义的方法构成「所有对象共有的最小行为集」[^object-src]。下文依据本机 **Oracle JDK 17.0.20.1**（`$JAVA_HOME`=`/home/charlie/workspace/sdks/jdk-17`）自带源码包中的 `Object.java`，按成员出现顺序解析——侧重**为何存在、契约与 HotSpot 如何支撑、工程上如何用**；源码与本机实测用来锚定结论，而不是逐行注释。

源码路径：`$JAVA_HOME/lib/src.zip` → `java.base/java/lang/Object.java`[^object-src]。

运行与验证：同一套 Oracle JDK；工程 `learning-lab/java/java17-sources` 中的 `ObjectLayoutVerify` / `ObjectMethodsVerify` / `ObjectMonitorVerify`[^lab]。

## 类注释：根类型意味着什么

```java
/**
 * Class {@code Object} is the root of the class hierarchy.
 * Every class has {@code Object} as a superclass. All objects,
 * including arrays, implement the methods of this class.
 *
 * @see     java.lang.Class
 * @since   1.0
 */
public class Object {
```

把「万物皆对象」落成语言规则，有三层后果：

1. **统一多态入口**：任意引用都能当成 `Object` 传递，集合、反射、序列化等基础设施才能写通用逻辑。
2. **共享行为面**：相等、哈希、字符串表示、监视器等待/通知、浅拷贝入口都挂在根上，子类按需覆盖。
3. **数组也是对象**：`int[]`、`String[]` 有独立的运行时 `Class`，同样具备上述方法；数组还对 `clone()` 有特殊约定（见后文）。

JDK 17 这份 `Object.java` 里没有早期版本常见的 `registerNatives` 静态块；本地方法由 VM 侧绑定[^object-src]。这只是源文件形态上的事实，不影响对外 API。

---

## 无参构造 `Object()`：创建与初始化的分工

```java
@IntrinsicCandidate
public Object() {}
```

### 设计意图

`Object` 没有实例字段，构造器为空体。对象能否被使用，关键不在这段 Java 代码，而在 **`new` 字节码对应的分配与对象头安装**。构造器表达的是「初始化逻辑」；对空 `Object` 而言，初始化无可写内容。

### 原理：`new` 在 HotSpot 里做什么

执行 `Object obj = new Object();` 时，HotSpot 侧典型顺序是：

1. 在堆上分配对齐后的内存；
2. 写入对象头：Mark Word（初始 unlocked、尚未计算 identity hash）与 Klass 指针；
3. 调用 `<init>`（此处为空）；
4. 得到对象引用。

因此构造器执行时，对象已经在堆上，头信息已经可用。`@IntrinsicCandidate` 表示 HotSpot **可以**把该方法换成手写高效实现（intrinsic）；注解不改变语言语义，是否替换由 JVM 与平台决定[^object-src]。

### 对象头为何长这样

64 位 HotSpot（本机 Oracle JDK）在开启压缩类指针时，空 `Object` 经 JOL 观察为：8 字节 Mark + 4 字节压缩 Klass + 4 字节对齐填充 = **16 字节**。默认对象对齐是 8 字节（`-XX:ObjectAlignmentInBytes=8`），所以「实例 16 字节」来自 12 字节头再 pad，而不是「一律 16 字节对齐」[^shipilev][^lab]。

Mark Word 在 64 位 HotSpot 上承载锁态、分代年龄、identity hash 等信息。结合本机 JOL 与公开的 HotSpot 对象布局说明，无锁普通对象大致可理解为（高位在左）[^shipilev]：

```text
unused | hash(最多31 bit) | gap | age:4 | biased_lock:1 | lock:2
```

锁态低 2 位常见含义：`01` unlocked、`00` 轻量锁、`10` monitor、`11` marked。本机新建对象 Mark 为 `0x1`，JOL 标注 `non-biasable; age: 0`，与「默认未启用偏向锁、尚未计算 hash」一致[^lab]。

Identity hash 首次算出后写入 Mark 的 hash 域，供默认 `hashCode` / `identityHashCode` 稳定读取；JOL 在调用 `hashCode()` 后会打印出 `hash: 0x…`[^shipilev][^lab]。

### 用法与验证

日常几乎不会 `new Object()` 做业务建模；更常见的是理解「任意对象都有对象头」，从而解释锁、hash、GC age 等信息从何而来。

`ObjectLayoutVerify`（JOL）在本机 Oracle JDK 上再次运行得到（identity hash 每次进程不同，下列为当次输出）[^lab]：

```text
===== new Object() 后 =====
java.lang.Object object internals:
OFF  SZ   TYPE DESCRIPTION               VALUE
  0   8        (object header: mark)     0x0000000000000001 (non-biasable; age: 0)
  8   4        (object header: class)    0x00000d68
 12   4        (object alignment gap)
Instance size: 16 bytes

===== hashCode()=1149226626 (0x447fce82) 后 =====
java.lang.Object object internals:
OFF  SZ   TYPE DESCRIPTION               VALUE
  0   8        (object header: mark)     0x000000447fce8201 (hash: 0x447fce82; age: 0)
  8   4        (object header: class)    0x00000d68
 12   4        (object alignment gap)
Instance size: 16 bytes
```

`new` 后 Mark 为 `0x1`（尚未写入 hash）；调用 `hashCode()` 后同一 Mark 出现 `hash: 0x447fce82`，且返回值与该字段一致。Klass 压缩值与对齐填充在两次快照间不变。

---

## `getClass()`：运行时类型从哪里来

```java
@IntrinsicCandidate
public final native Class<?> getClass();
```

### 设计意图

类型系统在编译期用静态类型做检查，运行时仍需知道「堆上究竟是谁」。`getClass` 提供稳定、不可覆盖的运行时类型查询，供反射、日志、按真实类型分支等使用。Javadoc 还标明：返回的 `Class` 正是该类 `static synchronized` 方法所锁定的对象[^object-src]。

### 原理

- `final native`：子类不能改语义；VM 从对象头 Klass 映射到对应的 `java.lang.Class` 实例，常作 intrinsic。
- 源码签名是 `Class<?>`，但编译器按 JLS 将调用处类型当作 `Class<? extends |X|>`，其中 `|X|` 是接收表达式静态类型的擦除[^jls-class-literal]。因此 `Number n; n.getClass()` 可直接赋给 `Class<? extends Number>`。
- 实例 `synchronized` 锁 `this`；`static synchronized` 锁该类的 `Class` 对象——与「用 `Foo.class` 或该类实例的运行时 Class」描述的是同一把类锁（对具体实例，`getClass()` 给出的是该实例的真实类型对应的 Class）。

### 用法

| 场景 | 更合适的选择 |
|------|----------------|
| 需要实例真实类型 | `obj.getClass()` |
| 静态上下文、字面指定类型 | `Foo.class` |
| 泛型擦除后的静态类型 | 注意 `List<String>` 擦除后是 `List`，返回类型不是 `Class<? extends List<String>>` |

`ObjectMethodsVerify` 本机输出[^lab]：

```text
===== getClass =====
n.getClass()=java.lang.Integer
list.getClass()=java.util.ArrayList
list.getClass() == ArrayList.class: true
```

---

## `hashCode()`：为哈希表准备的整数指纹

```java
@IntrinsicCandidate
public native int hashCode();
```

### 设计意图

哈希表（如 `HashMap`）用整数把键分散到桶里，再在桶内用 `equals` 确认。`hashCode` 就是这枚指纹。契约写在 Javadoc 里，目的是保证「相等对象能进同一查找路径」，并允许冲突存在[^object-src]。

### 原理：契约为何如此

1. **同一次运行内一致**（参与 `equals` 的信息未改）：否则同一键刚 put 完就可能 get 不到。跨进程不要求相同，否则会限制实现（例如不能用与地址/随机相关的策略）。
2. **`equals` 为 true ⇒ hash 必须相同**：桶索引先依赖 hash；违反则逻辑相等的键落在不同桶。
3. **`equals` 为 false 不要求 hash 不同**：冲突合法；区分度越高，链表/树化压力越小。

`@implSpec`：默认实现在合理范围内尽量让不同对象得到不同整数。在本机 Oracle HotSpot 上，未重写的 `hashCode` 与 `System.identityHashCode` 一致：首次计算后 identity hash 写入对象 Mark Word，之后稳定读取（JOL 可见 `hash:` 字段）；并非简单「把堆地址截断当 hash」[^shipilev][^lab]。对象处于加锁等状态时，hash 仍须在逻辑上保持「算过就不变」（具体存放位置由 VM 处理）。

未重写时，默认 hash 标识的是**对象身份**；已重写的类型（如 `String`）走自己的内容哈希，与默认路径无关。

### 用法

- 按字段定义逻辑相等时，**用同一组字段**同时实现 `equals` 与 `hashCode`（如 `Objects.hash(...)`）。
- 需要始终拿 identity hash（即使子类重写了 `hashCode`）时用 `System.identityHashCode`。

`ObjectMethodsVerify` 本机输出[^lab]：

```text
===== hashCode / identityHashCode =====
a.hashCode() twice same: true
a.hashCode()==b.hashCode(): false
identityHashCode(a)==a.hashCode(): true
===== 只重写 equals 不重写 hashCode =====
p1.equals(p2)=true
p1.hashCode()=254961745
p2.hashCode()=820795191
map.get(p2)=null
```

`equals` 为 true，但默认 `hashCode`（identity）不同 → `get` 为 `null`。

HashMap 定位桶时会对 `hashCode` 做扰动（`h ^ (h >>> 16)`），再 `(n-1) & hash`；这是表实现细节，强化了「hash 分布」对性能的影响。

---

## `equals(Object)`：等价关系的根实现

```java
public boolean equals(Object obj) {
    return (this == obj);
}
```

### 设计意图

默认实现采用**引用相等**：只有同一个对象才相等。这是最细的等价关系——每个等价类通常只有一个元素。内容相等由子类按领域重写；根类型先给出一个永远满足契约、且与 identity hash 自然一致的基线[^object-src]。

### 原理：五条契约各自防什么

Javadoc 要求非空引用上的等价关系：

| 性质 | 若破坏，典型后果 |
|------|------------------|
| 自反 `x.equals(x)` | 集合「含自身」类逻辑异常 |
| 对称 | `HashSet`/`HashMap` 一侧能找到、另一侧找不到 |
| 传递 | 分组、去重语义崩坏 |
| 一致 | 未改关键字段时结果漂移，结构损坏 |
| `x.equals(null)==false` | 调用方可依赖不抛 NPE 的约定 |

`@apiNote`：重写 `equals` 时通常必须重写 `hashCode`，否则破坏「相等 ⇒ 同 hash」[^object-src]。

继承 + `instanceof` 时容易伤对称性：父类只比部分字段、子类要求更严，会出现 `p.equals(cp) != cp.equals(p)`。若子类在对方是父类时「放宽」比较，又常伤传递性。Effective Java 建议对值类型谨慎做可继承的 equals，或用 `getClass()` 限制同类型，或改用组合[^ej]。

### 用法

本机 `ObjectMethodsVerify`[^lab]：

```text
===== equals 默认 =====
x.equals(x)=true
x.equals(y)=false
x.equals(null)=false
===== equals 对称性破坏 =====
p.equals(cp)=true
cp.equals(p)=false
```

同类型字段相等的常见写法：

```java
@Override
public boolean equals(Object o) {
    if (this == o) return true;
    if (o == null || getClass() != o.getClass()) return false;
    Person other = (Person) o;
    return age == other.age && Objects.equals(name, other.name);
}

@Override
public int hashCode() {
    return Objects.hash(name, age);
}
```

---

## `clone()`：浅拷贝入口

```java
@IntrinsicCandidate
protected native Object clone() throws CloneNotSupportedException;
```

### 设计意图

提供「复制自身」的钩子：默认语义是**浅拷贝**——新实例字段按赋值拷贝，引用字段仍指向原对象内部结构。是否允许拷贝由 `Cloneable` 标记；`Object` 自身未实现该接口[^object-src]。

### 原理

1. 未实现 `Cloneable` → `CloneNotSupportedException`；**数组类型视为实现了 `Cloneable`**，且 `T[].clone()` 返回 `T[]`。
2. 实现了则分配同运行时类实例并拷贝字段（浅）。
3. 惯例（非绝对硬性）：`clone() != this`、`clone().getClass() == getClass()`；一路调用 `super.clone()` 更易满足后者。

VM 侧按对象大小做内存级拷贝并安装对象头；Java 层负责门禁与约定。`Cloneable` 是标记接口，没有 `clone` 方法本身，设计上常被批评；许多代码改用拷贝构造或静态工厂，尤其需要深拷贝时更清晰[^ej]。

### 用法

```java
final class Cell implements Cloneable {
    int value;
    @Override
    public Cell clone() {
        try {
            return (Cell) super.clone();
        } catch (CloneNotSupportedException e) {
            throw new AssertionError(e);
        }
    }
}
```

本机 `ObjectMethodsVerify`[^lab]：

```text
===== clone / toString =====
clone != original: true
same class: true
value copied: true
after mutate original, copy.value=7
array clone independent: true
toString=java.lang.Object@553e7138
expectedPrefix=java.lang.Object@553e7138
toString matches formula: true
===== 未实现 Cloneable 时 super.clone 失败 =====
clone failed: CloneNotSupportedException
```

---

## `toString()`：给人看的默认描述

```java
public String toString() {
    return getClass().getName() + "@" + Integer.toHexString(hashCode());
}
```

### 设计意图

日志、调试、异常信息里需要一串可读文本。默认实现不尝试描述业务字段，只给出「类型名 + identity 向哈希的十六进制」，保证任意对象都能打印且实现廉价[^object-src]。

### 原理与用法

公式依赖当前 `hashCode()`：未重写时即 identity hash 的 hex；重写了 `hashCode` 则跟内容哈希走。Javadoc 建议子类给出更有信息量的表示，且不保证跨时间、跨 JVM 稳定。

领域模型、DTO、作为日志关键字的对象通常应重写；纯内部哨兵对象可保留默认。上节实测中 `toString` 与公式拼接一致（当次为 `java.lang.Object@553e7138`）[^lab]。

---

## 对象监视器：`wait` / `notify` 的共享模型

`notify`、`notifyAll`、`wait` 都建立在**对象监视器**上：

- 成为持有者的途径：实例 `synchronized` 方法、`synchronized (obj)`、或对该 `Class` 执行 `static synchronized`[^object-src]。
- 同一时刻至多一个线程持有某对象的 monitor。
- HotSpot 用 Mark Word 编码锁态，竞争加剧时可膨胀为重量级监视器；等待线程进入 wait set，通知从 wait set 中唤醒[^shipilev]。
- 未持有 monitor 时调用这些方法 → `IllegalMonitorStateException`。

本机 `ObjectMonitorVerify`[^lab]：

```text
===== 未持锁调用 wait → IMSE =====
caught: IllegalMonitorStateException
```

---

## `notify()`：唤醒一个等待者

```java
@IntrinsicCandidate
public final native void notify();
```

### 设计意图与原理

在条件可能已满足时，让**某一个**在该对象上 `wait` 的线程离开 wait set。选哪个由实现决定，不可依赖顺序。被唤醒线程**不会立刻执行临界区**：必须等通知方释放 monitor 后，再与其它线程正常竞争锁——否则会破坏互斥[^object-src]。

### 用法

适合「确定只有一类等待条件、唤醒一个即可」的场景。多条件共享一把锁时，误唤醒无关等待者的风险更高，往往更宜 `notifyAll` + `while` 检查条件。

本机 `ObjectMonitorVerify`[^lab]：

```text
===== notify 唤醒 =====
waiter: entering wait
main: notify
waiter: resumed after notify
```

---

## `notifyAll()`：唤醒全部等待者

```java
@IntrinsicCandidate
public final native void notifyAll();
```

### 设计意图与用法

语义同 `notify` 的持锁前提与「唤醒后仍要抢锁」；差别是清空（唤醒）该对象 wait set 上的**所有**线程。多等待者、条件谓词不同时，广播再各自用 `while` 过滤，正确性通常更好，代价是更多线程被调度起来抢锁。

---

## `wait()`：无限期等待的入口

```java
public final void wait() throws InterruptedException {
    wait(0L);
}
```

### 设计意图与原理

无参 `wait` 表示「不按超时醒来」，一直等到通知、中断或虚假唤醒等。实现上直接委托 `wait(0L)`；与带 nanos 重载的规范一致：超时参数全 0 表示忽略时间维度[^object-src]。

调用方仍须持有 monitor。异常：`IllegalMonitorStateException`；`InterruptedException`（抛出时清除中断状态）。

### 用法

生产代码几乎总是 `while (!condition) { obj.wait(); }`，与下一节相同，以消化虚假唤醒与「通知时条件又变」的情况。

---

## `wait(long timeoutMillis)`：带超时的等待

```java
public final native void wait(long timeoutMillis) throws InterruptedException;
```

### 原理

在持有 monitor 的前提下：

1. 进入该对象的 wait set；
2. **释放本对象上的同步声明**（其它对象上已持有的锁不释放）；
3. 暂停直至 notify/notifyAll、中断、超时或虚假唤醒；
4. 重新获得 monitor 后，恢复进入 wait 前的锁状态，再返回。

`timeoutMillis == 0` 与无参类似（不因超时返回）；`> 0` 则大约在指定毫秒后可返回。负值不合法。Javadoc 将其行为与 `wait(timeoutMillis, 0)` 对齐说明[^object-src]。

本机 `ObjectMonitorVerify`[^lab]：

```text
===== wait(timeout) 超时返回 =====
wait(50) returned, elapsedMs≈50
```

---

## `wait(long, int)`：纳秒参数与实现策略

```java
public final void wait(long timeoutMillis, int nanos) throws InterruptedException {
    if (timeoutMillis < 0) {
        throw new IllegalArgumentException("timeoutMillis value is negative");
    }
    if (nanos < 0 || nanos > 999999) {
        throw new IllegalArgumentException(
            "nanosecond timeout value out of range");
    }
    if (nanos > 0 && timeoutMillis < Long.MAX_VALUE) {
        timeoutMillis++;
    }
    wait(timeoutMillis);
}
```

### 设计意图与原理

对外提供毫秒 + 纳秒的超时接口；底层 `wait(long)` 只有毫秒粒度。源码策略是：参数合法后，若 `nanos > 0` 且毫秒未达 `Long.MAX_VALUE`，则将毫秒**加一**再下传——把不足一毫秒的部分向上取整，而不是丢弃纳秒信息后假装仍是原毫秒值[^object-src]。规范叙述的总时长约为 `1000000L * timeoutMillis + nanos` 纳秒；两者都为 0 则忽略时间。

本机 `ObjectMonitorVerify`[^lab]：

```text
===== wait(long,int) 参数校验 =====
wait(-1,0): timeoutMillis value is negative
wait(0,1000000): nanosecond timeout value out of range
```

### 用法：条件等待模板

虚假唤醒与「醒了条件仍不成立」都必须由应用处理[^object-src]：

```java
synchronized (obj) {
    while (!condition) {
        obj.wait(timeoutMillis, nanos);
    }
    // 条件已成立
}
```

---

## `finalize()`：已弃用的终结钩子

```java
@Deprecated(since="9")
protected void finalize() throws Throwable { }
```

### 设计意图与原理

历史上用于对象不可达后做清理。`Object` 的实现为空。语言与实现都**不保证**调用时机、线程、跨对象顺序；同一对象至多终结一次；终结中未捕获异常被忽略；甚至可能在 finalize 里再次发布 `this` 造成「复活」。这些问题使 finalization 难以用于可靠资源管理，故自 Java 9 起正式废弃[^object-src][^jls-finalize]。

子类若覆盖，**不会**自动链式调用父类 finalize，需要时显式 `super.finalize()`（通常放在 `finally`）。

### 用法（JDK 17 仍保留符号）

堆外资源优先：

- 显式释放 + `AutoCloseable` / try-with-resources；
- `java.lang.ref.Cleaner` 或 `PhantomReference` 等。

新代码以这些机制为主；`finalize` 仅在阅读遗留代码或理解 JLS 终结语义时仍会遇到。

---

## 成员索引（对照 `Object.java`）

| 源码成员 | 形态 | 本节 |
|----------|------|------|
| 类 Javadoc | 注释 | [类注释](#类注释根类型意味着什么) |
| `Object()` | intrinsic 空构造 | [无参构造](#无参构造-object创建与初始化的分工) |
| `getClass()` | `final native` | [`getClass`](#getclass运行时类型从哪里来) |
| `hashCode()` | `native` | [`hashCode`](#hashcode为哈希表准备的整数指纹) |
| `equals(Object)` | `return this == obj` | [`equals`](#equalsobject等价关系的根实现) |
| `clone()` | `protected native` | [`clone`](#clone浅拷贝入口) |
| `toString()` | Java 拼接 | [`toString`](#tostring给人看的默认描述) |
| `notify()` / `notifyAll()` | `final native` | [notify](#notify唤醒一个等待者) / [notifyAll](#notifyall唤醒全部等待者) |
| `wait()` / `wait(long)` / `wait(long,int)` | 委托 / native / 校验+进位 | [wait](#wait无限期等待的入口) 起三节 |
| `finalize()` | `@Deprecated` 空体 | [finalize](#finalize已弃用的终结钩子) |

---

## 参考文献

[^object-src]: Oracle JDK 17.0.20.1，`$JAVA_HOME/lib/src.zip` 内 `java.base/java/lang/Object.java`（本机 `$JAVA_HOME`=`/home/charlie/workspace/sdks/jdk-17`；`release` 中 `JAVA_RUNTIME_VERSION=17.0.20.1+1-LTS-4`，`IMPLEMENTOR=Oracle Corporation`）。

[^jls-class-literal]: James Gosling et al., *The Java Language Specification, Java SE 17 Edition*, §15.8.2 Class Literals. <https://docs.oracle.com/javase/specs/jls/se17/html/jls-15.html#jls-15.8.2>

[^jls-finalize]: *The Java Language Specification, Java SE 17 Edition*, §12.6 Finalization of Class Instances. <https://docs.oracle.com/javase/specs/jls/se17/html/jls-12.html#jls-12.6>

[^shipilev]: Aleksey Shipilëv, *Java Objects Inside Out*（HotSpot 对象布局、identity hash 与 Mark Word）. <https://shipilev.net/jvm/objects-inside-out/>

[^ej]: Joshua Bloch, *Effective Java*, 3rd ed., Addison-Wesley, 2018. 相关条目：equals / hashCode；谨慎使用 `Cloneable`.

[^lab]: 验证环境：Oracle JDK 17.0.20.1（HotSpot，`java.vendor=Oracle Corporation`，`$JAVA_HOME=/home/charlie/workspace/sdks/jdk-17`）。工程 `learning-lab/java/java17-sources`；类 `ObjectLayoutVerify`、`ObjectMethodsVerify`、`ObjectMonitorVerify`。文中粘贴的输出均为该环境下重新执行 `mvn … exec:java` 的当次结果（identity hash / `toString` 后缀随进程变化）。
