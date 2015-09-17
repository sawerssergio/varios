import time

from openerp import tools, osv
from openerp import models, fields, api

class res_company(models.Model):
    _inherit = 'res.company'
    branch_office = fields.Char()
    invoice_legend = fields.Text()

