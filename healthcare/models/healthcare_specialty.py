from odoo import fields, models


class HealthcareSpecialty(models.Model):
    _name = "healthcare.specialty"
    _description = "Medical Specialty"
    _order = "name"

    name = fields.Char(required=True, translate=True)
    doctor_ids = fields.One2many("res.users", "healthcare_specialty_id", string="Doctors")

    _name_uniq = models.Constraint("UNIQUE(name)", "A specialty with this name already exists.")
