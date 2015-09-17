import time

from openerp import tools, osv
from openerp import models, fields, api

class account_invoice(models.Model):
    _inherit = 'account.invoice'
    control_code = fields.Char('Control Code', readonly=True, copy=False)




