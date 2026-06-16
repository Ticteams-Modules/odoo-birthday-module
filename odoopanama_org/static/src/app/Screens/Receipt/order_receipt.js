/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(OrderReceipt.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this._processReceiptFE();
    },

   
    _processReceiptFE() {
        const receiptData = this.props.data;

        if (!receiptData.company) {
            receiptData.company = this.pos.company;
        }


        if (receiptData.invoice_number || receiptData.is_cpe !== undefined) {
            receiptData.company.is_cpe = receiptData.is_cpe;
            receiptData.company.env = receiptData.env;
            receiptData.company.billing_point = receiptData.billing_point;
            receiptData.company.invoice_number = receiptData.invoice_number;
            receiptData.company.type_of_invoice_document = receiptData.type_of_invoice_document;

            const pacSignature = this.pos.company._raw?.pac_signature ||
                               this.pos.company.pac_signature || '';
            if (pacSignature) {
                receiptData.company.pac_signature = pacSignature;
            }
        }
    },

    generateQR(content) {
        if (typeof qrcode === 'function' && content) {
            const qr = qrcode(0, 'M');
            qr.addData(content);
            qr.make();
            return qr.createDataURL(4);
        }
        return '';
    }
});