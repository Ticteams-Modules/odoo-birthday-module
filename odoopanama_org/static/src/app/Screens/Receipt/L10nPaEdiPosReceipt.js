/** @odoo-module **/

import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class L10nPaEdiPosReceipt extends OrderReceipt {
    // Usar el template del padre (OrderReceipt) que incluye nuestras extensiones en receipt_header.xml
    // static template = "odoopanama_org_pos.L10nPaEdiPosReceipt"; // Template no existe, usar el del padre

    static props = {
        ...OrderReceipt.props,
        order: { type: Object, optional: true },
    };

    setup() {
        super.setup();
        this.pos = usePos();
        this._processReceipt();
    }

    /**
     * Procesar datos del recibo para facturación electrónica
     * NOTA: Este componente no se usa actualmente, la funcionalidad está en order_receipt.js
     */
    _processReceipt() {
        const receiptData = this.props.data;

        // Asignar company desde this.pos.company si no existe
        if (!receiptData.company) {
            receiptData.company = this.pos.company;
        }

        // Agregar datos de facturación electrónica a company
        if (receiptData.invoice_number || receiptData.is_cpe !== undefined) {
            receiptData.company.is_cpe = receiptData.is_cpe;
            receiptData.company.env = receiptData.env;
            receiptData.company.billing_point = receiptData.billing_point;
            receiptData.company.invoice_number = receiptData.invoice_number;

            // Agregar pac_signature si existe
            const pacSignature = this.pos.company._raw?.pac_signature ||
                               this.pos.company.pac_signature || '';
            if (pacSignature) {
                receiptData.company.pac_signature = pacSignature;
            }
        }

        if (receiptData.orderlines) {
            const orderLines = this.props.order.get_orderlines();
            receiptData.orderlines = receiptData.orderlines.map((line, index) => {
                const originalLine = orderLines[index];
                const default_code = originalLine ? originalLine.get_product().default_code || '' : '';
                const tax_amount = originalLine ? originalLine.get_tax() : 0;

                return {
                    ...line,
                    default_code,
                    tax_amount,
                };
            });
        }

        receiptData.qr_code = this.generateQR(this.props.order);
        this._processedReceipt = receiptData;
    }

    get order() {
        return this.props.order;
    }

    get receipt() {
        return this._processedReceipt;
    }

    generateQR(order) {
        const qrContent = order?.qrcontent;
        if (typeof qrcode === 'function' && qrContent) {
            const qr = qrcode(0, 'M');
            qr.addData(qrContent);
            qr.make();
            return qr.createDataURL(4);
        }
        return '';
    }
}
