from odoo import fields, models


class EstatePropertyTag(models.Model):
    _name = "estate.property.tag"
    _description = "Real Estate Property Tag"

    _name_uniq = models.Constraint(
        "UNIQUE(name)",
        "A property tag name must be unique.",
    )

    name = fields.Char(required=True)
