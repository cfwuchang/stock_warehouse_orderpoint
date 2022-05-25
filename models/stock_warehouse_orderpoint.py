from odoo import api, fields, models, tools, _
from collections import defaultdict
from odoo.tools import add, float_compare, frozendict, split_every, format_date

class stockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    @api.depends('product_id', 'location_id', 'product_id.stock_move_ids', 'product_id.stock_move_ids.state', 'product_id.stock_move_ids.product_uom_qty')
    def _compute_qty(self):
        orderpoints_contexts = defaultdict(lambda: self.env['stock.warehouse.orderpoint'])
        aa=self.env['product.product'].search([])
        for orderpoint in self:
            if not orderpoint.product_id or not orderpoint.location_id:
                orderpoint.qty_on_hand = False
                orderpoint.qty_forecast = False
                continue
            orderpoint_context = orderpoint._get_product_context()
            product_context = frozendict({**self.env.context, **orderpoint_context})
            orderpoints_contexts[product_context] |= orderpoint
        for orderpoint_context, orderpoints_by_context in orderpoints_contexts.items():
            products_qty = orderpoints_by_context.product_id.with_context(orderpoint_context)._product_available()
            # products_qty_in_progress = orderpoints_by_context._quantity_in_progress()
            for orderpoint in orderpoints_by_context:
                orderpoint.qty_on_hand = products_qty[orderpoint.product_id.id]['qty_available']
                # bb = products_qty[orderpoint.product_id.id]['virtual_available']+ products_qty_in_progress[orderpoint.id]
                orderpoint.qty_forecast = orderpoint.product_id.virtual_available
                # orderpoint.qty_forecast = products_qty[orderpoint.product_id.id]['virtual_available']+ products_qty_in_progress[orderpoint.id]
                # for i in aa:
                #     if i.id==orderpoint.product_id.id:
                #         if bb !=i.virtual_available:
                #             orderpoint.qty_forecast = i.virtual_available

    # @api.onchange('qty_forecast')
    @api.depends('qty_multiple', 'qty_forecast', 'product_min_qty', 'product_max_qty')
    def _compute_qty_to_order(self):
        for orderpoint in self:
            if not orderpoint.product_id or not orderpoint.location_id:
                orderpoint.qty_to_order = False
                continue
            qty_to_order = 0.0
            rounding = orderpoint.product_uom.rounding
            if float_compare(orderpoint.qty_forecast, orderpoint.product_min_qty, precision_rounding=rounding) < 0:
                # qty_to_order = max(orderpoint.product_min_qty, orderpoint.product_max_qty) - orderpoint.qty_forecast
                qty_to_order = max(orderpoint.product_min_qty, orderpoint.product_max_qty) - orderpoint.product_id.virtual_available

                remainder = orderpoint.qty_multiple > 0 and qty_to_order % orderpoint.qty_multiple or 0.0
                if float_compare(remainder, 0.0, precision_rounding=rounding) > 0:
                    qty_to_order += orderpoint.qty_multiple - remainder
            orderpoint.qty_to_order = qty_to_order
