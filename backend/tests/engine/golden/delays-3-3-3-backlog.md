# Delays 3/3/3 with starting backlog, pass-through Orders: Weeks 1-8 worked by hand

Independent check (2026-11-17): agrees. No human is in the loop, so a separate reviewer
worked Weeks 1-8 by hand from the Week sequence and this set-up, without seeing this table
or the engine, and then compared its result with `delays-3-3-3-backlog.json`: 0 mismatches
in all 32 rows, the Orders and the totals.

This table is the source of `delays-3-3-3-backlog.json`. It was worked by hand from the Week
sequence (PRD FR-26, addendum §B), not produced by the engine under test.

## Set-up

- 4 Roles; order, shipping and production delay 3; starting inventory 0 and starting backlog 4
  per Seat; 4 in every slot; holding 0.50 and backorder 1.00 per unit per Week; 8 Weeks.
- Customer demand 4 in Weeks 1-4, 8 from Week 5.
- Orders: the Retailer orders customer demand; every other Seat orders its own incoming order.
- Slots at delay 3: the Retailer has no order slot; every other Seat has 3 order slots; every
  Seat has 3 goods slots (production for the Factory); the Factory has 3 production-order slots.
- The chain starts with 48 units: 0 in inventory, 36 in shipping slots, 12 in production slots.

## How each Week is worked

1. Receive `goods_slots[0]` into inventory.
2. Amount to ship = incoming order + backlog; ship the smaller of inventory and that amount;
   the rest is backlog.
3. Goods pipelines move up one slot and take the upstream Seat's shipment this Week; the
   Factory's production pipeline takes the Order entering production (`production_orders[0]`).
4. Cost = 0.50 × inventory + 1.00 × backlog on those balances.
5. Orders: each order pipeline drops index 0 and appends the downstream Seat's Order; the
   Factory's `production_orders` appends its own Order.

Slots below are the state after the Week opened (step 3), "arrives soonest" first. Timing at
delay 3: an Order placed in Week t is received in t+3, a shipment sent in t arrives in t+3, and
a Factory Order placed in t enters production in t+3 and reaches Factory inventory in t+6.

Derived by hand: every Seat starts with 0 inventory, so each Week it can ship only what was
delivered (4). Every shipment is 4 and every goods slot holds 4 throughout. The Wholesaler's
incoming order in Week t is the Retailer's Order of t-3, so the step reaches the Wholesaler in
Week 8; the Wholesaler's first Order of 8 (Week 8) reaches the Distributor in Week 11, outside
this table. The Distributor and Factory therefore see 4 every Week.

## Weeks

### Week 1

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 4.00 | — | (4, 4, 4) | — |
| Wholesaler | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 4.00 | (4, 4, 4) | (4, 4, 4) | — |
| Distributor | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 4.00 | (4, 4, 4) | (4, 4, 4) | — |
| Factory | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 4.00 | (4, 4, 4) | (4, 4, 4) | (4, 4, 4) |

Unit check: 48 on hand and in transit = 48 + 4 entered production − 4 delivered.

### Week 2

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 8.00 | — | (4, 4, 4) | — |
| Wholesaler | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 8.00 | (4, 4, 4) | (4, 4, 4) | — |
| Distributor | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 8.00 | (4, 4, 4) | (4, 4, 4) | — |
| Factory | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 8.00 | (4, 4, 4) | (4, 4, 4) | (4, 4, 4) |

Unit check: 48 on hand and in transit = 48 + 8 entered production − 8 delivered.

### Week 3

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 12.00 | — | (4, 4, 4) | — |
| Wholesaler | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 12.00 | (4, 4, 4) | (4, 4, 4) | — |
| Distributor | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 12.00 | (4, 4, 4) | (4, 4, 4) | — |
| Factory | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 12.00 | (4, 4, 4) | (4, 4, 4) | (4, 4, 4) |

Unit check: 48 on hand and in transit = 48 + 12 entered production − 12 delivered.

### Week 4

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 16.00 | — | (4, 4, 4) | — |
| Wholesaler | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 16.00 | (4, 4, 4) | (4, 4, 4) | — |
| Distributor | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 16.00 | (4, 4, 4) | (4, 4, 4) | — |
| Factory | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 16.00 | (4, 4, 4) | (4, 4, 4) | (4, 4, 4) |

Unit check: 48 on hand and in transit = 48 + 16 entered production − 16 delivered.

### Week 5

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 8 | 4 | 4 | 0 | 8 | 8 | 8.00 | 24.00 | — | (4, 4, 4) | — |
| Wholesaler | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 20.00 | (4, 4, 4) | (4, 4, 4) | — |
| Distributor | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 20.00 | (4, 4, 4) | (4, 4, 4) | — |
| Factory | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 20.00 | (4, 4, 4) | (4, 4, 4) | (4, 4, 4) |

Unit check: 48 on hand and in transit = 48 + 20 entered production − 20 delivered.

### Week 6

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 8 | 4 | 4 | 0 | 12 | 8 | 12.00 | 36.00 | — | (4, 4, 4) | — |
| Wholesaler | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 24.00 | (4, 4, 8) | (4, 4, 4) | — |
| Distributor | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 24.00 | (4, 4, 4) | (4, 4, 4) | — |
| Factory | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 24.00 | (4, 4, 4) | (4, 4, 4) | (4, 4, 4) |

Unit check: 48 on hand and in transit = 48 + 24 entered production − 24 delivered.

### Week 7

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 8 | 4 | 4 | 0 | 16 | 8 | 16.00 | 52.00 | — | (4, 4, 4) | — |
| Wholesaler | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 28.00 | (4, 8, 8) | (4, 4, 4) | — |
| Distributor | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 28.00 | (4, 4, 4) | (4, 4, 4) | — |
| Factory | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 28.00 | (4, 4, 4) | (4, 4, 4) | (4, 4, 4) |

Unit check: 48 on hand and in transit = 48 + 28 entered production − 28 delivered.

### Week 8

| Role | Incoming order | Incoming delivery | Shipped | Inventory | Backlog | Order | Cost | Total incl. Week | Order slots | Goods slots | Production orders |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| Retailer | 8 | 4 | 4 | 0 | 20 | 8 | 20.00 | 72.00 | — | (4, 4, 4) | — |
| Wholesaler | 8 | 4 | 4 | 0 | 8 | 8 | 8.00 | 36.00 | (8, 8, 8) | (4, 4, 4) | — |
| Distributor | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 32.00 | (4, 4, 4) | (4, 4, 4) | — |
| Factory | 4 | 4 | 4 | 0 | 4 | 4 | 4.00 | 32.00 | (4, 4, 4) | (4, 4, 4) | (4, 4, 4) |

Unit check: 48 on hand and in transit = 48 + 32 entered production − 32 delivered.

## Totals after Week 8 (the Game finishes in Week 8)

| Role | Total cost |
|---|---:|
| Retailer | 72.00 |
| Wholesaler | 36.00 |
| Distributor | 32.00 |
| Factory | 32.00 |
