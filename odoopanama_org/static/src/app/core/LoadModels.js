/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    /**
     * Procesar datos del servidor después de cargarlos
     * Agregar mapeos para journals y tipos de documento latam
     */
    async processServerData(...args) {
        await super.processServerData(...args);

        // Cargar y mapear journals de facturación
        this.journals = this.models['account.journal']?.getAll() || [];

        // Mapeo por ID para acceso rápido
        this.journal_by_id = Object.fromEntries(
            this.journals.map(j => [j.id, j])
        );

        // Cargar tipos de documento latam
        this.l10n_latam_document_types =
            this.models['l10n_latam.document.type']?.getAll() || [];

        // Cargar tipos de identificación latam
        this.l10n_latam_identification_types =
            this.models['l10n_latam.identification.type']?.getAll() || [];
    },
});
