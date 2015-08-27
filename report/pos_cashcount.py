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

        for detail in details:
            print detail.pieces
    

        docargs = {
                'doc_model':report.model,
                'docs':current_session,
                'details':details,
        }
        return report_obj.render('pos_kingdom.report_cashcount',docargs)

        
