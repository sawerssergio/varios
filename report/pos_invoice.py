# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from num2words import num2words
from openerp.osv import osv
from openerp.tools.translate import _


class PosInvoiceReport(osv.AbstractModel):
    _name = 'report.pos_kingdom.report_invoice'

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

    def render_html(self, cr, uid, ids, data=None, context=None):
        report_obj = self.pool['report']
        posorder_obj = self.pool['pos.order']
        report = report_obj._get_report_from_name(cr, uid, 'pos_kingdom.report_invoice')
        selected_orders = posorder_obj.browse(cr, uid, ids, context=context)

        ids_to_print = []
        invoiced_posorders_ids = []
        for order in selected_orders:
            if order.invoice_id:
                ids_to_print.append(order.invoice_id.id)
                invoiced_posorders_ids.append(order.id)

        not_invoiced_orders_ids = list(set(ids) - set(invoiced_posorders_ids))
        if not_invoiced_orders_ids:
            not_invoiced_posorders = posorder_obj.browse(cr, uid, not_invoiced_orders_ids, context=context)
            not_invoiced_orders_names = list(map(lambda a: a.name, not_invoiced_posorders))
            raise osv.except_osv(_('Error!'), _('No link to an invoice for %s.' % ', '.join(not_invoiced_orders_names)))

        docargs = {
            'doc_ids': ids_to_print,
            'doc_model': report.model,
            'docs': selected_orders,
            'num2words': self.get_amount_literal,
        }
        return report_obj.render(cr, uid, ids, 'pos_kingdom.report_invoice', docargs, context=context)
