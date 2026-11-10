package shop.model

import shop.util.Clock

data class Order(val id: Int)

enum class Status { ABERTO, FECHADO }

typealias Id = Int
