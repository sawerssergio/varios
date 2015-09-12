from openerp import api,models

class CashCount(models.AbstractModel):
    _name = 'report.pos_kingdom.report_cashcount'
    @api.multi
    def render_html(self,data=None):
        print 'Render Report Cash Count'
        report_obj = self.env['report']
        report = report_obj._get_report_from_name('pos_kingdom.report_cashcount')
        pos_session_obj = self.env['pos.session']
        current_session = pos_session_obj.browse([self._ids[0]])
        opening_details = current_session.opening_details_ids
        details = current_session.details_ids
        details_bob = [] 
        details_usd = []
        total_bob = 0 
        total_usd = 0
        totals = []

        for detail in details:
            currency_name = detail.journal_cashbox_ref.currency_name
            if currency_name == 'USD':
                details_usd.append(detail)

            if currency_name == 'BOB':
                details_bob.append(detail)

        for detail in details_bob:
            total_bob += detail.pieces*detail.number_closing
        for detail in details_usd:
            total_usd += detail.pieces*detail.number_closing
        totals.append(total_bob)
        totals.append(total_usd)

        docargs = {
                'doc_model':report.model,
                'docs':current_session,
                'details':details_bob,
                'details_usd':details_usd,
                'totals':totals,
        }
        return report_obj.render('pos_kingdom.report_cashcount',docargs)

        
