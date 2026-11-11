from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Real Estate Property Offer"
    _order = "price desc"

    _check_price = models.Constraint(
        "CHECK(price > 0)",
        "The offer price must be strictly positive.",
    )

    price = fields.Float()
    status = fields.Selection(
        selection=[
            ("accepted", "Accepted"),
            ("refused", "Refused"),
        ],
        copy=False,
    )
    partner_id = fields.Many2one("res.partner", string="Partner", required=True)
    property_id = fields.Many2one("estate.property", string="Property", required=True)
    property_type_id = fields.Many2one(
        related="property_id.property_type_id",
        store=True,
    )
    validity = fields.Integer(string="Validity (days)", default=7)
    date_deadline = fields.Date(
        string="Deadline",
        compute="_compute_date_deadline",
        inverse="_inverse_date_deadline",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("property_id"):
                continue
            property_ = self.env["estate.property"].browse(vals["property_id"])
            best_price = max(property_.offer_ids.mapped("price"), default=0.0)
            if float_compare(vals.get("price", 0.0), best_price, precision_digits=2) < 0:
                raise UserError(self.env._(
                    "The offer must be higher than %(price).2f, the best existing offer.",
                    price=best_price,
                ))
        offers = super().create(vals_list)
        offers.property_id.filtered(lambda p: p.state == "new").state = "offer_received"
        return offers

    def _get_start_date(self):
        # create_date is only set once the record is saved: fall back to today.
        self.ensure_one()
        if self.create_date:
            return self.create_date.date()
        return fields.Date.context_today(self)

    @api.depends("create_date", "validity")
    def _compute_date_deadline(self):
        for record in self:
            record.date_deadline = fields.Date.add(record._get_start_date(), days=record.validity)

    def _inverse_date_deadline(self):
        for record in self:
            if record.date_deadline:
                record.validity = (record.date_deadline - record._get_start_date()).days

    def action_accept(self):
        for record in self:
            other_accepted = record.property_id.offer_ids.filtered(
                lambda offer: offer.status == "accepted" and offer != record
            )
            if other_accepted:
                raise UserError(self.env._("An offer has already been accepted for this property."))
            record.status = "accepted"
            record.property_id.write({
                "buyer_id": record.partner_id.id,
                "selling_price": record.price,
                "state": "offer_accepted",
            })
        return True

    def action_refuse(self):
        for record in self:
            record.status = "refused"
        return True
