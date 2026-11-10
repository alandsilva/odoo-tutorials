from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class HealthcareAppointment(models.Model):
    _name = "healthcare.appointment"
    _description = "Medical Appointment"
    _order = "start desc"

    name = fields.Char(string="Reference", required=True, readonly=True, copy=False, default="New")
    doctor_id = fields.Many2one(
        "res.users",
        string="Doctor",
        required=True,
        index=True,
        domain=lambda self: self.env["res.users"]._healthcare_doctor_domain(),
    )
    specialty_id = fields.Many2one(related="doctor_id.healthcare_specialty_id")
    patient_id = fields.Many2one(
        "res.users",
        string="Patient",
        required=True,
        index=True,
        domain=lambda self: self.env["res.users"]._healthcare_patient_domain(),
        default=lambda self: self._default_patient_id(),
    )
    start = fields.Datetime(required=True)
    duration = fields.Float(string="Duration (hours)", required=True, default=0.5)
    stop = fields.Datetime(compute="_compute_stop", store=True)
    state = fields.Selection(
        selection=[
            ("booked", "Booked"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="booked",
        copy=False,
    )
    reason = fields.Char(string="Reason for Visit")
    notes = fields.Html(string="Doctor's Notes", groups="healthcare.group_healthcare_doctor")

    def _default_patient_id(self):
        user = self.env.user
        if user.has_group("healthcare.group_healthcare_patient") and not user._is_healthcare_doctor():
            return user
        return False

    @api.depends("start", "duration")
    def _compute_stop(self):
        for record in self:
            record.stop = record.start and record.start + timedelta(hours=record.duration)

    @api.depends("patient_id", "doctor_id", "start")
    def _compute_display_name(self):
        for record in self:
            record.display_name = " - ".join(filter(None, [record.patient_id.name, record.doctor_id.name]))

    @api.constrains("duration")
    def _check_duration(self):
        if any(record.duration <= 0 for record in self):
            raise ValidationError(self.env._("An appointment must last a positive amount of time."))

    @api.constrains("doctor_id", "patient_id", "start", "stop", "state")
    def _check_availability(self):
        Appointment = self.sudo()
        for record in self.filtered(lambda a: a.state != "cancelled"):
            if record.doctor_id == record.patient_id:
                raise ValidationError(self.env._("A doctor cannot book an appointment with themselves."))
            if not record.doctor_id._healthcare_is_within_schedule(record.start, record.stop):
                raise ValidationError(self.env._(
                    "%(doctor)s does not consult at that time. Use “Book an Appointment” to see the free slots.",
                    doctor=record.doctor_id.name,
                ))
            overlapping = Appointment.search_count([
                ("id", "!=", record.id),
                ("state", "!=", "cancelled"),
                ("start", "<", record.stop),
                ("stop", ">", record.start),
                "|", ("doctor_id", "=", record.doctor_id.id), ("patient_id", "=", record.patient_id.id),
            ], limit=1)
            if overlapping:
                raise ValidationError(self.env._(
                    "This time slot is no longer available for %(doctor)s or %(patient)s.",
                    doctor=record.doctor_id.name,
                    patient=record.patient_id.name,
                ))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code("healthcare.appointment") or "New"
        appointments = super().create(vals_list)
        if not self.env.su and not self.env.user._is_healthcare_doctor():
            if any(a.start < fields.Datetime.now() for a in appointments):
                raise UserError(self.env._("You cannot book an appointment in the past."))
        return appointments

    def write(self, vals):
        if (
            vals.get("state") == "done"
            and not self.env.su
            and not self.env.user._is_healthcare_doctor()
        ):
            raise UserError(self.env._("Only doctors can mark an appointment as done."))
        return super().write(vals)

    def action_done(self):
        if any(record.state != "booked" for record in self):
            raise UserError(self.env._("Only booked appointments can be marked as done."))
        self.state = "done"
        return True

    def action_cancel(self):
        if any(record.state == "done" for record in self):
            raise UserError(self.env._("A completed appointment cannot be cancelled."))
        self.state = "cancelled"
        return True

    def action_reset(self):
        self.state = "booked"
        return True
