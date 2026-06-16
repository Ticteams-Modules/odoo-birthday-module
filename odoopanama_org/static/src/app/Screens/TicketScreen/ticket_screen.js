/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { _t } from "@web/core/l10n/translation";

patch(TicketScreen.prototype, {
    setup() {
        super.setup();
        if (this.props.destinationOrder) {
            this.props.destinationOrder.set_partner(null);
        }
    },

    _getSearchFields() {
        return {
            INVOICE_NUMBER: {
                repr: (order) => order.number || '',
                displayName: _t("Invoice Number"),
                modelField: "number",
            },
            ...super._getSearchFields()
        };
    },

    getFilteredOrderList() {
        const orders = super.getFilteredOrderList();

        if (!this._state?.ui?.searchDetails) {
            return orders;
        }

        const { fieldName, searchTerm } = this._state.ui.searchDetails;

        if (fieldName === 'INVOICE_NUMBER' && searchTerm) {
            const lowerSearchTerm = searchTerm.toLowerCase();
            return orders.filter(order =>
                (order.number || '').toLowerCase().includes(lowerSearchTerm)
            );
        }

        return orders;
    },

    addAdditionalRefundInfo(order, destinationOrder) {
        super.addAdditionalRefundInfo(...arguments);
        const accountMoveId = order.raw?.account_move;
        if (accountMoveId) {
            destinationOrder.original_move_id = accountMoveId;
        }
    },

    async postRefund(destinationOrder) {
        await super.postRefund(...arguments);

        if (this.pos.config.auto_go_to_payment_on_refund) {
            const orderlines = destinationOrder.get_orderlines?.() || destinationOrder.lines || [];
            if (orderlines.length > 0) {
                this.pos.showScreen('PaymentScreen', { orderUuid: destinationOrder.uuid });
            }
        }
    }
});
