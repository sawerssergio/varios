from openerp import api,models
from num2words import num2words

class BolivianInvoiceReport(models.AbstractModel):
    _name = 'report.pos_kingdom.bolivian_invoice'

    def get_amount_literal(self,number):
        literal = num2words(int(number),lang='es')
        decimal = str(number-int(number))[2:]
        decimal_str = self.get_decimal_literal(int(decimal))
        res = literal.upper() + " " + decimal_str
        return res
    
    def get_decimal_literal(self,number):
        if number < 10:
            return "0"+str(number)+"/100 Bs"
        else:
            return str(number)+"/100 Bs"

    @api.multi
    def render_html(self,data=None):
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('pos_kingdom.bolivian_invoice')
        posorder_obj = self.env['pos.order']
        selected_orders = posorder_obj.browse([self._ids[0]])
        print selected_orders[0].name
        ids_to_print = []
        invoiced_posorders_ids = []
        for order in selected_orders:
            if order.invoice_id:
                ids_to_print.append(order.invoice_id.id)
                invoiced_posorders_ids.append(order.id)

        docargs = {
                'doc_ids': ids_to_print,
                'doc_model': report.model,
                'docs': selected_orders,
                'num2words': self.get_amount_literal,
        }
        return report_obj.render('pos_kingdom.bolivian_invoice', docargs)
