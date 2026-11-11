from odoo import fields, models


class EstatePropertyType(models.Model):
    _name = "estate.property.type"
    _description = "Real Estate Property Type"
    _order = "sequence, name"

    _name_uniq = models.Constraint(
        "UNIQUE(name)",
        "A property type name must be unique.",
    )

    name = fields.Char(required=True)
    sequence = fields.Integer(default=1, help="Used to order property types. Lower is better.")
    property_ids = fields.One2many("estate.property", "property_type_id", string="Properties")
