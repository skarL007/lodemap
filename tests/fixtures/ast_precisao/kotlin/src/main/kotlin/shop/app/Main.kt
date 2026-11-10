@file:JvmName("MainKt")
package shop.app

import shop.model.Order
import shop.model.Order as Pedido
import shop.model.Status
import shop.util.*
import shop.util.Clock.now
import shop.util.weird
import shop.ext.toTitle
import shop.config.VERSION
import shop.legacy.Legacy
import kotlin.collections.List
// import shop.model.Fantasma
/* import shop.model.Fantasma */

val texto = """
import shop.model.Fantasma
"""
val outro = "import shop.model.Fantasma"

fun main() {
    println(slug("x") + now() + "a".toTitle() + VERSION + weird())
}
