from odoo import api, fields, models
from odoo.exceptions import ValidationError

WEEKDAYS = [
    ("0", "Monday"),
    ("1", "Tuesday"),
    ("2", "Wednesday"),
    ("3", "Thursday"),
    ("4", "Friday"),
    ("5", "Saturday"),
    ("6", "Sunday"),
]


class HealthcareSchedule(models.Model):
    """Weekly opening hours of a doctor, expressed in the doctor's timezone."""
    _name = "healthcare.schedule"
    _description = "Doctor Availability"
    _order = "doctor_id, dayofweek, hour_from"

    doctor_id = fields.Many2one(
        "res.users",
        string="Doctor",
        required=True,
        ondelete="cascade",
        domain=lambda self: self.env["res.users"]._healthcare_doctor_domain(),
        default=lambda self: self.env.user if self.env.user._is_healthcare_doctor() else False,
    )
    dayofweek = fields.Selection(WEEKDAYS, string="Day of Week", required=True, default="0")
    hour_from = fields.Float(string="From", required=True, default=9.0)
    hour_to = fields.Float(string="To", required=True, default=17.0)

    @api.constrains("hour_from", "hour_to")
    def _check_hours(self):
        for record in self:
            if not 0 <= record.hour_from < record.hour_to <= 24:
                raise ValidationError(self.env._("Availability must start before it ends, within the same day."))
