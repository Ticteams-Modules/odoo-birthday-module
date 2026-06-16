/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(ProductScreen.prototype, {
    /**
     * Validar que el producto tenga impuestos configurados
     */
    async _clickProduct(event) {
        const product = event.detail;
        if (!product.taxes_id?.length) {
            this.dialog.add(AlertDialog, {
                title: _t("Error"),
                body: _t("No puede seleccionar productos sin impuestos configurados."),
            });
            return false;
        }
        return await super._clickProduct(event);
    },
});

