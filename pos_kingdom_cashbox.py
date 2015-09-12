import time

from openerp import tools, osv
from openerp import models, fields, api

class account_journal(models.Model):
    _inherit = 'account.journal'
    def get_currency_id(self,currency_name):
        currency_obj = self.env['res.currency']
        currencys = currency_obj.search([])
        for currency in currencys:
            if currency_name == 'BOB':
                if currency.name == 'BOB':
                    return currency.id

            if currency_name == 'USD':
                if currency.name == 'USD':
                    return currency.id

    @api.v8
    @api.multi
    def _default_cashbox_line_ids(self,context=None):
        # Return a list of coins in BOB and USD.
        result = [
                dict(pieces=value,currency_id=self.get_currency_id('BOB')) for value in [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200]
        ]

        usd = [
                dict(pieces=value,currency_id=self.get_currency_id('USD')) for value in [1, 5, 10, 20, 50, 100]
        ]

        for coin in usd:
            result.append(coin)
        
        return result

    cashbox_line_ids = fields.One2many('account.journal.cashbox.line', 'journal_id', 'CashBox',default=_default_cashbox_line_ids,copy=True)

class cashbox_memory(models.TransientModel):
    _name = 'cashbox.memory'

    pieces = fields.Float("Unit of Currency")
    journal_cashbox_line_id = fields.Integer("ID REF")
    bank_statement_id = fields.Integer("Bank Statement ID")
    currency_name = fields.Char("Currency Name")


class account_cashbox_line(models.Model):
    _inherit = 'account.cashbox.line'

    journal_cashbox_ref = fields.Many2one('account.journal.cashbox.line','Journal Cashbox')
    currency_name = fields.Char(related='journal_cashbox_ref.currency_name',store=True)

    @api.model
    def create(self,values):
        print values
        cashbox_memory_model = self.env['cashbox.memory']
        bank_statement_model = self.env['account.bank.statement']
        current_bank_statement = bank_statement_model.browse(values['bank_statement_id'])
        journal_cashbox_lines = current_bank_statement.journal_id.cashbox_line_ids
        for journal_cashbox_line in journal_cashbox_lines: 
            if journal_cashbox_line.pieces == values['pieces']:
                cashbox_memory_line = cashbox_memory_model.search([['bank_statement_id','=',values['bank_statement_id']],['pieces','=',values['pieces']]])
                if len(cashbox_memory_line) == 0: 
                    values['journal_cashbox_ref'] = journal_cashbox_line.id
                    cashbox_memory_model.create({'pieces':values['pieces'],'journal_cashbox_line_id':values['journal_cashbox_ref'],'bank_statement_id':values['bank_statement_id'],'currency_name':journal_cashbox_line.currency_name})
                    new_id = super(account_cashbox_line,self).create(values)
                    return new_id
                else:
                    if cashbox_memory_line.currency_name == 'BOB':
                        right_journal_cashbox = journal_cashbox_line.search([['pieces','=',values['pieces']],['currency_name','=','USD']])
                        values['journal_cashbox_ref'] = right_journal_cashbox.id


                    if cashbox_memory_line.currency_name == 'USD':
                        right_journal_cashbox = journal_cashbox_line.search([['pieces','=',values['pieces']],['currency_name','=','BOB']])
                        values['journal_cashbox_ref'] = right_journal_cashbox.id
                        
                    new_id = super(account_cashbox_line,self).create(values)
                    return new_id

    
class account_journal_cashbox_line(models.Model):
    _inherit = 'account.journal.cashbox.line'

    currency_id = fields.Many2one('res.currency','Currency',ondelete='cascade')
    currency_name = fields.Char(related='currency_id.name',store=True)




