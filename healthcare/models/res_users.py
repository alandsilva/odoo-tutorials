from datetime import datetime, time, timedelta

import pytz

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    healthcare_specialty_id = fields.Many2one("healthcare.specialty", string="Specialty")
    healthcare_schedule_ids = fields.One2many("healthcare.schedule", "doctor_id", string="Availabilities")

    def _healthcare_doctor_domain(self):
        """Bookable doctors: users of the Doctor group who practice a specialty
        (administrators inherit the Doctor group without being practitioners)."""
        return [
            ("all_group_ids", "in", self.env.ref("healthcare.group_healthcare_doctor").ids),
            ("healthcare_specialty_id", "!=", False),
        ]

    def _healthcare_patient_domain(self):
        return [("all_group_ids", "in", self.env.ref("healthcare.group_healthcare_patient").ids)]

    def _is_healthcare_doctor(self):
        self.ensure_one()
        return self.has_group("healthcare.group_healthcare_doctor")

    # ------------------------------------------------------------------
    # Availability helpers (doctors)
    # ------------------------------------------------------------------

    def _healthcare_tz(self):
        self.ensure_one()
        return pytz.timezone(self.tz or "UTC")

    def _healthcare_is_within_schedule(self, start, stop):
        """Return whether [start, stop) (naive UTC datetimes) fits in one of
        the doctor's weekly availabilities."""
        self.ensure_one()
        tz = self._healthcare_tz()
        local_start = pytz.utc.localize(start).astimezone(tz)
        local_stop = pytz.utc.localize(stop).astimezone(tz)
        if local_start.date() != local_stop.date():
            return False
        hour_from = local_start.hour + local_start.minute / 60
        hour_to = local_stop.hour + local_stop.minute / 60
        return any(
            schedule.hour_from <= hour_from and hour_to <= schedule.hour_to
            for schedule in self.sudo().healthcare_schedule_ids
            if schedule.dayofweek == str(local_start.weekday())
        )

    def _healthcare_get_free_slots(self, day, duration):
        """Return the free (start, stop) naive UTC datetimes of the doctor on
        ``day`` (a date in the doctor's timezone), cut in ``duration`` hours."""
        self.ensure_one()
        if duration <= 0:
            return []
        tz = self._healthcare_tz()
        step = timedelta(hours=duration)
        candidates = []
        for schedule in self.sudo().healthcare_schedule_ids.filtered(
            lambda s: s.dayofweek == str(day.weekday())
        ):
            local_cursor = tz.localize(datetime.combine(day, time()) + timedelta(hours=schedule.hour_from))
            local_end = tz.localize(datetime.combine(day, time()) + timedelta(hours=schedule.hour_to))
            while local_cursor + step <= local_end:
                start = local_cursor.astimezone(pytz.utc).replace(tzinfo=None)
                candidates.append((start, start + step))
                local_cursor += step
        if not candidates:
            return []

        busy = self.env["healthcare.appointment"].sudo().search([
            ("doctor_id", "=", self.id),
            ("state", "!=", "cancelled"),
            ("start", "<", max(stop for __, stop in candidates)),
            ("stop", ">", min(start for start, __ in candidates)),
        ])
        now = fields.Datetime.now()
        return sorted(
            (start, stop) for start, stop in candidates
            if start >= now and not any(a.start < stop and start < a.stop for a in busy)
        )
