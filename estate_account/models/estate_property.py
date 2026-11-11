from odoo import models
from odoo.fields import Command

COMMISSION_RATE = 0.06
ADMINISTRATIVE_FEES = 100.00


class EstateProperty(models.Model):
    _inherit = "estate.property"

    def action_sold(self):
        res = super().action_sold()
        for record in self:
            self.env["account.move"].create({
                "partner_id": record.buyer_id.id,
                "move_type": "out_invoice",
                "invoice_line_ids": [
                    Command.create({
                        "name": self.env._("Commission (6%% of %(price).2f)", price=record.selling_price),
                        "quantity": 1,
                        "price_unit": record.selling_price * COMMISSION_RATE,
                    }),
                    Command.create({
                        "name": self.env._("Administrative fees"),
                        "quantity": 1,
                        "price_unit": ADMINISTRATIVE_FEES,
                    }),
                ],
            })
        return res
