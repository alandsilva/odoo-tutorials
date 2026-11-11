from odoo import api, fields, models
from odoo.exceptions import UserError


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
    validity = fields.Integer(string="Validity (days)", default=7)
    date_deadline = fields.Date(
        string="Deadline",
        compute="_compute_date_deadline",
        inverse="_inverse_date_deadline",
    )

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
