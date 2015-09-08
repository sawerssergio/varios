import time

from openerp import tools, osv
from openerp import models, fields, api

class account_cashbox_line(models.Model):
    _inherit = 'account.cashbox.line'

    journal_cashbox_ref = fields.Many2one('account.journal.cashbox.line','Journal Cashbox')

    @api.model
    def create(self,values):
        bank_statement_model = self.env['account.bank.statement']
        current_bank_statement = bank_statement_model.browse(values['bank_statement_id'])
        cashbox_line_ids = current_bank_statement.journal_id.cashbox_line_ids
        for cashbox_line_id in cashbox_line_ids: 
            if cashbox_line_id.pieces == values['pieces']:
                values['journal_cashbox_ref'] = cashbox_line_id.id
        new_id = super(account_cashbox_line,self).create(values)
        return new_id
    
class account_journal_cashbox_line(models.Model):
    _inherit = 'account.journal.cashbox.line'

    currency_id = fields.Many2one('res.currency','Currency',ondelete='cascade')
    currency_name = fields.Char(related='currency_id.name',store=True)




