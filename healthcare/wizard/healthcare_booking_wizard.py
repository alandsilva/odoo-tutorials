from datetime import timedelta

from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class HealthcareBookingWizard(models.TransientModel):
    _name = "healthcare.booking.wizard"
    _description = "Book an Appointment"

    specialty_id = fields.Many2one("healthcare.specialty", string="Specialty")
    doctor_id = fields.Many2one(
        "res.users",
        string="Doctor",
        required=True,
        domain="[('id', 'in', allowed_doctor_ids)]",
    )
    allowed_doctor_ids = fields.Many2many("res.users", compute="_compute_allowed_doctor_ids")
    patient_id = fields.Many2one(
        "res.users",
        string="Patient",
        required=True,
        domain=lambda self: self.env["res.users"]._healthcare_patient_domain(),
        default=lambda self: self.env["healthcare.appointment"]._default_patient_id(),
    )
    is_doctor = fields.Boolean(default=lambda self: self.env.user._is_healthcare_doctor())
    date = fields.Date(required=True, default=lambda self: fields.Date.context_today(self) + timedelta(days=1))
    duration = fields.Float(string="Duration (hours)", required=True, default=0.5)
    reason = fields.Char(string="Reason for Visit")
    slot_ids = fields.One2many(
        "healthcare.booking.wizard.slot",
        "wizard_id",
        string="Available Slots",
        compute="_compute_slot_ids",
        store=True,
        readonly=False,
    )

    @api.depends("specialty_id")
    def _compute_allowed_doctor_ids(self):
        domain = self.env["res.users"]._healthcare_doctor_domain()
        for wizard in self:
            extra = [("healthcare_specialty_id", "=", wizard.specialty_id.id)] if wizard.specialty_id else []
            wizard.allowed_doctor_ids = self.env["res.users"].search(domain + extra)

    @api.depends("doctor_id", "date", "duration")
    def _compute_slot_ids(self):
        for wizard in self:
            slots = []
            if wizard.doctor_id and wizard.date:
                slots = wizard.doctor_id._healthcare_get_free_slots(wizard.date, wizard.duration)
            wizard.slot_ids = [Command.clear()] + [
                Command.create({"start": start, "stop": stop}) for start, stop in slots
            ]

    def action_book(self):
        self.ensure_one()
        slot = self.slot_ids.filtered("selected")
        if len(slot) != 1:
            raise UserError(self.env._("Please select exactly one time slot."))
        appointment = self.env["healthcare.appointment"].create({
            "doctor_id": self.doctor_id.id,
            "patient_id": self.patient_id.id,
            "start": slot.start,
            "duration": self.duration,
            "reason": self.reason,
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": "healthcare.appointment",
            "res_id": appointment.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.onchange("specialty_id")
    def _onchange_specialty_id(self):
        if self.specialty_id and self.doctor_id.healthcare_specialty_id != self.specialty_id:
            self.doctor_id = False

    def action_next_day(self):
        return self._reopen(days=1)

    def action_previous_day(self):
        return self._reopen(days=-1)

    def _reopen(self, days):
        self.ensure_one()
        self.date += timedelta(days=days)
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "name": self.env._("Book an Appointment"),
        }


class HealthcareBookingWizardSlot(models.TransientModel):
    _name = "healthcare.booking.wizard.slot"
    _description = "Available Appointment Slot"
    _order = "start"

    wizard_id = fields.Many2one("healthcare.booking.wizard", required=True, ondelete="cascade")
    start = fields.Datetime(required=True)
    stop = fields.Datetime(required=True)
    selected = fields.Boolean()
