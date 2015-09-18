from openerp import api,models
from num2words import num2words
from datetime import datetime

class BolivianInvoiceReport(models.AbstractModel):
    _name = 'report.pos_kingdom.bolivian_invoice'

    def get_qr_string(self,order):  
      invoice_number = order.invoice_id.number
      amount = str(order.invoice_id.amount_total)
      date_invoice = order.invoice_id.date_invoice
      date_object = datetime.strptime(date_invoice,'%Y-%m-%d')
      strtime = datetime.strftime(date_object,'%d/%m/%Y')
      authorization = order.session_id.config_id.authorization
      company_nit = order.company_id.vat
      partner_nit = order.partner_id.vat
      control_code = order.invoice_id.control_code
      qr_gen = "/report/barcode/QR/"
      qr_string = company_nit + "|" + invoice_number + "|" + authorization + "|" + strtime + "|" + amount + "|" + amount + "|" + control_code + "|" + partner_nit + "|0|0|0|0"
      qr_url = qr_gen + qr_string
      print qr_url
      return qr_url

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
        qr_string = ""
        date_invoice = ""
        for order in selected_orders:
            if order.invoice_id:
                ids_to_print.append(order.invoice_id.id)
                invoiced_posorders_ids.append(order.id)
                qr_string = self.get_qr_string(order)
                date_inv = order.invoice_id.date_invoice
                date_obj = datetime.strptime(date_inv,'%Y-%m-%d')
                date_invoice = datetime.strftime(date_obj,'%d/%m/%Y')

        paid = 0
        due = 0
        for statement in selected_orders.statement_ids:
            if statement.amount < 0:
                due = abs(statement.amount)
            else:
                paid = statement.amount
 
        docargs = {
                'doc_ids': ids_to_print,
                'doc_model': report.model,
                'docs': selected_orders,
                'num2words': self.get_amount_literal,
                'paid':paid,
                'due':due,
                'qr_string':qr_string,
                'date_invoice':date_invoice,
        }
        return report_obj.render('pos_kingdom.bolivian_invoice', docargs)
