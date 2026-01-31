-- Migración: Agregar campos SumUp a tabla pagos
-- Fecha: 2025-01-15
-- Descripción: Agrega campos para integración con SumUp en kiosko
-- Versión: Simple (sin procedimientos)

-- Agregar campos (ignorar error si ya existen)
ALTER TABLE `pagos` 
ADD COLUMN `sumup_checkout_id` VARCHAR(100) NULL COMMENT 'ID del checkout de SumUp',
ADD COLUMN `sumup_checkout_url` TEXT NULL COMMENT 'URL del checkout de SumUp para generar QR',
ADD COLUMN `sumup_merchant_code` VARCHAR(50) NULL COMMENT 'Código del comerciante SumUp';

-- Crear índice (ignorar error si ya existe)
CREATE INDEX `idx_pagos_sumup_checkout_id` ON `pagos` (`sumup_checkout_id`);

