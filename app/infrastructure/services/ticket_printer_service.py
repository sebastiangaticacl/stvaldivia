"""
Servicio de Impresión de Tickets
Genera e imprime tickets con código de barras cuando se completa una venta
"""
import os
import io
import subprocess
import platform
from typing import Optional, Dict, Any
from datetime import datetime
from flask import current_app
import barcode
from barcode.writer import ImageWriter
from PIL import Image, ImageDraw, ImageFont
import qrcode
import logging

logger = logging.getLogger(__name__)


class TicketPrinterService:
    """Servicio para generar e imprimir tickets con código de barras"""
    
    def __init__(self, printer_name: Optional[str] = None):
        """
        Inicializa el servicio de impresión
        
        Args:
            printer_name: Nombre de la impresora (opcional, usa la predeterminada si no se especifica)
        """
        self.system = platform.system()
        self.printer_name = printer_name or self._get_default_printer()
    
    def _get_default_printer(self) -> Optional[str]:
        """Obtiene la impresora predeterminada del sistema"""
        try:
            if self.system == "Windows":
                # Windows: usar wmic
                result = subprocess.run(
                    ['wmic', 'printer', 'where', 'default=true', 'get', 'name'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    return lines[1].strip()
            elif self.system == "Darwin":  # macOS
                # macOS: usar lpstat
                result = subprocess.run(
                    ['lpstat', '-d'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if ':' in result.stdout:
                    return result.stdout.split(':')[1].strip()
            elif self.system == "Linux":
                # Linux: usar lpstat
                result = subprocess.run(
                    ['lpstat', '-d'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if ':' in result.stdout:
                    return result.stdout.split(':')[1].strip()
        except Exception as e:
            logger.warning(f"No se pudo obtener impresora predeterminada: {e}")
        
        return None
    
    def generate_barcode_image(self, sale_id: str, format_code: str = "BMB") -> io.BytesIO:
        """
        Genera imagen de código de barras para un ticket
        IMPORTANTE: El código de barras debe contener SOLO el número del sale_id
        para que el bartender pueda escanearlo correctamente
        
        Args:
            sale_id: ID de la venta (puede tener prefijo o no)
            format_code: No se usa, se mantiene por compatibilidad
            
        Returns:
            BytesIO con la imagen del código de barras
        """
        # Normalizar sale_id (solo números) - CRÍTICO para que el scanner funcione
        numeric_id = ''.join(filter(str.isdigit, str(sale_id)))
        if not numeric_id:
            raise ValueError(f"Sale ID inválido: {sale_id}")
        
        # Crear código de barras Code128 con SOLO el número
        # El scanner del bartender lee este número y busca la venta en PHP POS
        code128 = barcode.get_barcode_class('code128')
        barcode_instance = code128(numeric_id, writer=ImageWriter())
        
        # Generar imagen
        img_buffer = io.BytesIO()
        barcode_instance.write(img_buffer)
        img_buffer.seek(0)
        
        return img_buffer
    
    def generate_ticket_image(
        self,
        sale_id: str,
        sale_data: Dict[str, Any],
        items: list,
        register_name: str = "POS",
        employee_name: str = "Vendedor"
    ) -> Image.Image:
        """
        Genera imagen completa del ticket con solo texto
        
        Args:
            sale_id: ID de la venta
            sale_data: Datos de la venta
            items: Lista de items
            register_name: Nombre de la caja
            employee_name: Nombre del vendedor
            
        Returns:
            PIL Image del ticket
        """
        # Configuración para impresora RPT006 (80mm térmica)
        # Según especificaciones: 72mm ancho útil, 8 dots/mm = 576 dots
        # Para PIL Image usamos 384px (equivalente a ~96 DPI estándar)
        width = 384  # Ancho estándar para impresoras térmicas 80mm
        margin = 15
        line_height = 22
        font_size = 13
        
        # Calcular altura total (incluyendo código QR)
        header_height = 45
        items_height = len(items) * 27
        qr_height = 150  # Altura para código QR (cuadrado)
        footer_height = 50   # Para números del ID
        total_height = header_height + items_height + qr_height + footer_height + (margin * 2) + 20
        
        # Crear imagen en modo portrait normal (texto horizontal)
        img = Image.new('RGB', (width, total_height), 'white')
        draw = ImageDraw.Draw(img)
        
        try:
            # Intentar cargar fuente
            try:
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
                font_bold = ImageFont.truetype("/System/Library/Fonts/Helvetica-Bold.ttc", font_size + 3)
            except:
                font = ImageFont.load_default()
                font_bold = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
            font_bold = ImageFont.load_default()
        
        y = margin
        
        # Encabezado - "BIMBA" centrado
        draw.text((width // 2, y), "BIMBA", fill='black', font=font_bold, anchor='mm')
        y += line_height + 18
        
        # Items - Lista de productos
        for item in items:
            item_name = item.get('name', 'Producto')[:28]
            quantity = item.get('quantity', 0)
            item_text = f"{quantity}x {item_name}"
            draw.text((margin, y), item_text, fill='black', font=font)
            y += line_height + 5
        
        y += 15
        
        # Código QR
        # Preferir qr_token del TicketEntrega (si existe); fallback a sale_id numérico.
        try:
            qr_payload = None
            try:
                qr_payload = (sale_data or {}).get('qr_token')
            except Exception:
                qr_payload = None
            qr_payload = str(qr_payload).strip() if qr_payload else ''

            display_code = None
            try:
                display_code = (sale_data or {}).get('ticket_display_code')
            except Exception:
                display_code = None
            display_code = str(display_code).strip() if display_code else ''

            numeric_sale_id = ''.join(filter(str.isdigit, str(sale_id)))
            if not numeric_sale_id:
                numeric_sale_id = str(sale_id)

            # Si no hay token, usar sale_id numérico
            if not qr_payload:
                qr_payload = numeric_sale_id
            
            # Generar código QR
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,  # Alta corrección de errores
                box_size=3,  # Tamaño adecuado para ticket térmico
                border=2
            )
            qr.add_data(qr_payload)
            qr.make(fit=True)
            
            # Crear imagen del QR
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
            # Redimensionar QR para que quepa bien en el ticket (cuadrado de ~150x150px)
            qr_size = min(150, width - (margin * 2))
            qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
            
            # Centrar horizontalmente en el ticket
            x_pos = (width - qr_size) // 2
            
            # Pegar código QR centrado
            img.paste(qr_img, (x_pos, y))
            y += qr_size + 10
            
            # Código visible debajo del QR:
            # - Si hay display_code del TicketEntrega, mostrarlo
            # - Si no, mostrar sale_id numérico como antes
            visible_code = display_code or numeric_sale_id

            # Texto "espaciado" para legibilidad si es corto
            if len(visible_code) <= 16:
                spaced = ' '.join(list(visible_code))
                draw.text((width // 2, y), spaced, fill='black', font=font_bold, anchor='mm')
                y += line_height + 5
                draw.text((width // 2, y), visible_code, fill='black', font=font, anchor='mm')
            else:
                draw.text((width // 2, y), visible_code, fill='black', font=font_bold, anchor='mm')
            
        except Exception as e:
            logger.error(f"Error al generar código de barras: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Si falla, solo mostrar el número
            numeric_sale_id = ''.join(filter(str.isdigit, str(sale_id)))
            if numeric_sale_id:
                draw.text((width // 2, y), numeric_sale_id, fill='black', font=font_bold, anchor='mm')
        
        # La impresora RPT006 imprime normal (portrait), no necesitamos rotar
        return img
    
    def open_cash_drawer(self) -> bool:
        """
        Abre el cajón de dinero conectado a la impresora
        Usa comandos ESC/POS estándar
        
        Returns:
            bool: True si se abrió correctamente, False en caso contrario
        """
        try:
            # Comando ESC/POS para abrir cajón: ESC p 0 25 250
            # ESC (27) p (112) 0 (tiempo en ms) 25 (tiempo en ms) 250 (tiempo en ms)
            drawer_command = b'\x1B\x70\x00\x19\xFA'  # ESC p 0 25 250
            
            if self.system == "Windows":
                return self._open_drawer_windows(drawer_command)
            elif self.system == "Darwin":  # macOS
                return self._open_drawer_macos(drawer_command)
            elif self.system == "Linux":
                return self._open_drawer_linux(drawer_command)
            else:
                logger.warning(f"Sistema operativo no soportado para abrir cajón: {self.system}")
                return False
        except Exception as e:
            logger.error(f"Error al abrir cajón de dinero: {e}")
            return False
    
    def _open_drawer_windows(self, command: bytes) -> bool:
        """Abre cajón en Windows"""
        try:
            if not self.printer_name:
                logger.warning("No se especificó nombre de impresora")
                return False
            
            # En Windows, enviar comando directamente a la impresora
            import win32print
            import win32api
            
            printer_handle = win32print.OpenPrinter(self.printer_name)
            try:
                win32print.StartDocPrinter(printer_handle, 1, ("Cash Drawer", None, "RAW"))
                win32print.StartPagePrinter(printer_handle)
                win32print.WritePrinter(printer_handle, command)
                win32print.EndPagePrinter(printer_handle)
                win32print.EndDocPrinter(printer_handle)
                logger.info(f"✅ Cajón abierto en impresora {self.printer_name}")
                return True
            finally:
                win32print.ClosePrinter(printer_handle)
        except ImportError:
            logger.warning("pywin32 no está instalado. Intentando método alternativo...")
            # Método alternativo usando archivo RAW
            try:
                printer_path = f"\\\\localhost\\{self.printer_name}"
                with open(printer_path, 'wb') as printer:
                    printer.write(command)
                logger.info(f"✅ Cajón abierto (método alternativo) en {self.printer_name}")
                return True
            except Exception as e:
                logger.error(f"Error al abrir cajón (método alternativo): {e}")
                return False
        except Exception as e:
            logger.error(f"Error al abrir cajón en Windows: {e}")
            return False
    
    def _open_drawer_macos(self, command: bytes) -> bool:
        """Abre cajón en macOS"""
        try:
            if not self.printer_name:
                # Usar impresora predeterminada
                result = subprocess.run(
                    ['lpstat', '-d'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    printer_name = result.stdout.split(':')[1].strip() if ':' in result.stdout else None
                else:
                    printer_name = None
            else:
                printer_name = self.printer_name
            
            if not printer_name:
                logger.warning("No se encontró impresora para abrir cajón")
                return False
            
            # Guardar comando en archivo temporal
            temp_file = f"/tmp/cash_drawer_{datetime.now().timestamp()}.raw"
            with open(temp_file, 'wb') as f:
                f.write(command)
            
            # Enviar a impresora usando lpr
            result = subprocess.run(
                ['lpr', '-P', printer_name, '-o', 'raw', temp_file],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Limpiar archivo temporal
            try:
                os.remove(temp_file)
            except:
                pass
            
            if result.returncode == 0:
                logger.info(f"✅ Cajón abierto en impresora {printer_name}")
                return True
            else:
                logger.error(f"Error al abrir cajón: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error al abrir cajón en macOS: {e}")
            return False
    
    def _open_drawer_linux(self, command: bytes) -> bool:
        """Abre cajón en Linux"""
        try:
            if not self.printer_name:
                # Usar impresora predeterminada
                result = subprocess.run(
                    ['lpstat', '-d'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    printer_name = result.stdout.split(':')[1].strip() if ':' in result.stdout else None
                else:
                    printer_name = None
            else:
                printer_name = self.printer_name
            
            if not printer_name:
                logger.warning("No se encontró impresora para abrir cajón")
                return False
            
            # Guardar comando en archivo temporal
            temp_file = f"/tmp/cash_drawer_{datetime.now().timestamp()}.raw"
            with open(temp_file, 'wb') as f:
                f.write(command)
            
            # Enviar a impresora usando lpr
            result = subprocess.run(
                ['lpr', '-P', printer_name, '-o', 'raw', temp_file],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Limpiar archivo temporal
            try:
                os.remove(temp_file)
            except:
                pass
            
            if result.returncode == 0:
                logger.info(f"✅ Cajón abierto en impresora {printer_name}")
                return True
            else:
                logger.error(f"Error al abrir cajón: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error al abrir cajón en Linux: {e}")
            return False

    def print_ticket(
        self,
        sale_id: str,
        sale_data: Dict[str, Any],
        items: list,
        register_name: str = "POS",
        employee_name: str = "Vendedor"
    ) -> bool:
        """
        Genera e imprime un ticket completo
        
        Args:
            sale_id: ID de la venta
            sale_data: Datos de la venta
            items: Lista de items
            register_name: Nombre de la caja
            employee_name: Nombre del vendedor
            
        Returns:
            True si se imprimió correctamente, False en caso contrario
        """
        try:
            # Generar imagen del ticket
            ticket_img = self.generate_ticket_image(
                sale_id=sale_id,
                sale_data=sale_data,
                items=items,
                register_name=register_name,
                employee_name=employee_name
            )
            
            # Guardar imagen sin rotar - como estaba funcionando
            temp_file = f"/tmp/ticket_{sale_id}_{datetime.now().timestamp()}.png"
            ticket_img.save(temp_file, 'PNG')
            
            # Imprimir según el sistema operativo
            success = False
            if self.system == "Windows":
                success = self._print_windows(temp_file)
            elif self.system == "Darwin":  # macOS
                success = self._print_macos(temp_file)
            elif self.system == "Linux":
                success = self._print_linux(temp_file)
            
            # Enviar comando de corte de papel después de imprimir
            # Agregar un pequeño delay antes del corte para asegurar que la impresión terminó
            if success:
                import time
                time.sleep(0.3)  # Esperar 300ms para que termine la impresión
                self._send_cut_command()
            
            # Limpiar archivo temporal
            try:
                os.remove(temp_file)
            except:
                pass
            
            if success:
                logger.info(f"Ticket {sale_id} impreso correctamente")
            else:
                logger.warning(f"No se pudo imprimir ticket {sale_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al imprimir ticket {sale_id}: {e}")
            return False
    
    def print_register_close_summary(
        self,
        register_name: str,
        employee_name: str,
        shift_date: str,
        opened_at: str,
        closed_at: str,
        total_sales: int,
        expected_cash: float,
        actual_cash: float,
        diff_cash: float,
        expected_debit: float,
        actual_debit: float,
        diff_debit: float,
        expected_credit: float,
        actual_credit: float,
        diff_credit: float,
        difference_total: float,
        is_balanced: bool,
        notes: str = ""
    ) -> bool:
        """
        Imprime un resumen del cierre de caja
        
        Returns:
            True si se imprimió correctamente, False en caso contrario
        """
        try:
            # Generar imagen del resumen
            summary_img = self.generate_register_close_summary_image(
                register_name=register_name,
                employee_name=employee_name,
                shift_date=shift_date,
                opened_at=opened_at,
                closed_at=closed_at,
                total_sales=total_sales,
                expected_cash=expected_cash,
                actual_cash=actual_cash,
                diff_cash=diff_cash,
                expected_debit=expected_debit,
                actual_debit=actual_debit,
                diff_debit=diff_debit,
                expected_credit=expected_credit,
                actual_credit=actual_credit,
                diff_credit=diff_credit,
                difference_total=difference_total,
                is_balanced=is_balanced,
                notes=notes
            )
            
            # Guardar temporalmente
            temp_file = f"/tmp/close_summary_{datetime.now().timestamp()}.png"
            summary_img.save(temp_file, 'PNG')
            
            # Imprimir según el sistema operativo
            success = False
            if self.system == "Windows":
                success = self._print_windows(temp_file)
            elif self.system == "Darwin":  # macOS
                success = self._print_macos(temp_file)
            elif self.system == "Linux":
                success = self._print_linux(temp_file)
            
            # Limpiar archivo temporal
            try:
                os.remove(temp_file)
            except:
                pass
            
            if success:
                logger.info(f"Resumen de cierre de caja impreso correctamente")
            else:
                logger.warning(f"No se pudo imprimir resumen de cierre de caja")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al imprimir resumen de cierre de caja: {e}")
            return False
    
    def generate_register_close_summary_image(
        self,
        register_name: str,
        employee_name: str,
        shift_date: str,
        opened_at: str,
        closed_at: str,
        total_sales: int,
        expected_cash: float,
        actual_cash: float,
        diff_cash: float,
        expected_debit: float,
        actual_debit: float,
        diff_debit: float,
        expected_credit: float,
        actual_credit: float,
        diff_credit: float,
        difference_total: float,
        is_balanced: bool,
        notes: str = ""
    ) -> Image.Image:
        """
        Genera imagen del resumen de cierre de caja
        """
        width = 384  # Ancho del ticket
        margin = 10
        line_height = 18
        font_size = 11
        
        # Calcular altura total
        lines_count = 25  # Aproximadamente
        if notes:
            lines_count += len(notes.split('\n')) + 2
        total_height = (lines_count * line_height) + (margin * 2) + 40
        
        img = Image.new('RGB', (width, total_height), 'white')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            font_bold = ImageFont.truetype("/System/Library/Fonts/Helvetica-Bold.ttc", font_size + 2)
        except:
            font = ImageFont.load_default()
            font_bold = ImageFont.load_default()
        
        y = margin
        
        # Encabezado
        draw.text((width // 2, y), "BIMBA", fill='black', font=font_bold, anchor='mm')
        y += line_height + 5
        draw.text((width // 2, y), "CIERRE DE CAJA", fill='black', font=font_bold, anchor='mm')
        y += line_height + 10
        
        # Información básica
        draw.text((margin, y), f"Caja: {register_name}", fill='black', font=font)
        y += line_height
        draw.text((margin, y), f"Cajero: {employee_name}", fill='black', font=font)
        y += line_height
        draw.text((margin, y), f"Fecha: {shift_date}", fill='black', font=font)
        y += line_height + 5
        
        # Línea separadora
        draw.line([(margin, y), (width - margin, y)], fill='black', width=1)
        y += line_height + 5
        
        # Resumen de ventas
        draw.text((margin, y), f"Total Ventas: {total_sales}", fill='black', font=font_bold)
        y += line_height + 5
        
        # Efectivo
        draw.text((margin, y), "EFECTIVO", fill='black', font=font_bold)
        y += line_height
        draw.text((margin + 10, y), f"Esperado: ${expected_cash:,.0f}", fill='black', font=font)
        y += line_height
        draw.text((margin + 10, y), f"Ingresado: ${actual_cash:,.0f}", fill='black', font=font)
        y += line_height
        diff_color = 'black' if diff_cash == 0 else ('green' if diff_cash > 0 else 'red')
        draw.text((margin + 10, y), f"Diferencia: ${diff_cash:,.0f}", fill=diff_color, font=font)
        y += line_height + 5
        
        # Débito
        draw.text((margin, y), "DÉBITO", fill='black', font=font_bold)
        y += line_height
        draw.text((margin + 10, y), f"Esperado: ${expected_debit:,.0f}", fill='black', font=font)
        y += line_height
        draw.text((margin + 10, y), f"Ingresado: ${actual_debit:,.0f}", fill='black', font=font)
        y += line_height
        diff_color = 'black' if diff_debit == 0 else ('green' if diff_debit > 0 else 'red')
        draw.text((margin + 10, y), f"Diferencia: ${diff_debit:,.0f}", fill=diff_color, font=font)
        y += line_height + 5
        
        # Crédito
        draw.text((margin, y), "CRÉDITO", fill='black', font=font_bold)
        y += line_height
        draw.text((margin + 10, y), f"Esperado: ${expected_credit:,.0f}", fill='black', font=font)
        y += line_height
        draw.text((margin + 10, y), f"Ingresado: ${actual_credit:,.0f}", fill='black', font=font)
        y += line_height
        diff_color = 'black' if diff_credit == 0 else ('green' if diff_credit > 0 else 'red')
        draw.text((margin + 10, y), f"Diferencia: ${diff_credit:,.0f}", fill=diff_color, font=font)
        y += line_height + 5
        
        # Línea separadora
        draw.line([(margin, y), (width - margin, y)], fill='black', width=1)
        y += line_height + 5
        
        # Diferencia total
        total_color = 'black' if difference_total == 0 else ('green' if difference_total > 0 else 'red')
        draw.text((margin, y), f"DIFERENCIA TOTAL: ${difference_total:,.0f}", fill=total_color, font=font_bold)
        y += line_height + 5
        
        # Estado
        status_text = "CAJA CUADRADA" if is_balanced else "CAJA DESCUADRADA"
        status_color = 'green' if is_balanced else 'red'
        draw.text((width // 2, y), status_text, fill=status_color, font=font_bold, anchor='mm')
        y += line_height + 5
        
        # Notas
        if notes:
            draw.line([(margin, y), (width - margin, y)], fill='black', width=1)
            y += line_height + 5
            draw.text((margin, y), "NOTAS:", fill='black', font=font_bold)
            y += line_height
            for note_line in notes.split('\n'):
                if note_line.strip():
                    draw.text((margin + 10, y), note_line[:40], fill='black', font=font)
                    y += line_height
        
        # Fecha y hora de cierre
        y += line_height
        draw.text((width // 2, y), f"Cerrado: {closed_at[:19]}", fill='black', font=font, anchor='mm')
        
        return img
    
    def _print_windows(self, file_path: str) -> bool:
        """Imprime en Windows"""
        try:
            if self.printer_name:
                cmd = ['mspaint', '/p', file_path]
            else:
                cmd = ['mspaint', '/p', file_path]
            subprocess.run(cmd, timeout=10, check=False)
            return True
        except Exception as e:
            logger.error(f"Error al imprimir en Windows: {e}")
            return False
    
    def _print_macos(self, file_path: str) -> bool:
        """Imprime en macOS usando lpr sin opciones de orientación (como Ctrl+P)"""
        try:
            # Usar lpr simple, igual que cuando se imprime con Ctrl+P
            cmd = ['lpr']
            if self.printer_name:
                cmd.extend(['-P', self.printer_name])
            # NO agregar opciones de orientación - dejar que la impresora use su configuración por defecto
            cmd.append(file_path)
            result = subprocess.run(cmd, timeout=10, capture_output=True, text=True, check=False)
            if result.returncode != 0:
                logger.error(f"Error al imprimir: {result.stderr}")
                return False
            return True
        except Exception as e:
            logger.error(f"Error al imprimir en macOS: {e}")
            return False
    
    def _print_linux(self, file_path: str) -> bool:
        """Imprime en Linux usando lp"""
        try:
            # Verificar si lp está disponible
            try:
                subprocess.run(['which', 'lp'], capture_output=True, check=True, timeout=2)
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                logger.warning("CUPS no está instalado en este sistema Linux. La impresión se deshabilitará automáticamente.")
                logger.info(f"Imagen del ticket guardada en: {file_path} (se puede imprimir manualmente o desde el cliente)")
                return False
            
            cmd = ['lp']
            if self.printer_name:
                cmd.extend(['-d', self.printer_name])
            cmd.append(file_path)
            subprocess.run(cmd, timeout=10, check=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error al imprimir en Linux (lp falló): {e}")
            logger.info(f"Imagen del ticket guardada en: {file_path} (se puede imprimir manualmente)")
            return False
        except Exception as e:
            logger.error(f"Error al imprimir en Linux: {e}")
            logger.info(f"Imagen del ticket guardada en: {file_path} (se puede imprimir manualmente)")
            return False
    
    def _send_cut_command(self) -> bool:
        """
        Envía comandos ESC/POS para cortar el papel y finalizar la impresión
        Incluye: feed de papel, corte, y reset para que la impresora no quede esperando
        """
        try:
            import time
            
            # Secuencia de comandos para finalizar correctamente:
            # 1. Feed de papel (avanzar líneas antes de cortar)
            # 2. Corte completo
            # 3. Reset para que la impresora no quede esperando
            
            # Feed de papel: ESC d (avanzar 3 líneas)
            feed_command = b'\x1B\x64\x03'  # ESC d 3 - Avanzar 3 líneas
            
            # Corte completo: GS V 0
            cut_command = b'\x1D\x56\x00'  # GS V 0 - Corte completo
            
            # Reset/Inicialización: ESC @ (resetea la impresora)
            reset_command = b'\x1B\x40'  # ESC @ - Reset
            
            # Combinar todos los comandos en una secuencia
            complete_command = feed_command + cut_command + reset_command
            
            # Pequeño delay para asegurar que la impresión anterior terminó
            time.sleep(0.5)
            
            if self.system == "Windows":
                return self._send_cut_windows(complete_command)
            elif self.system == "Darwin":  # macOS
                return self._send_cut_macos(complete_command)
            elif self.system == "Linux":
                return self._send_cut_linux(complete_command)
            else:
                logger.warning(f"Sistema operativo no soportado para corte: {self.system}")
                return False
        except Exception as e:
            logger.error(f"Error al enviar comando de corte: {e}")
            return False
    
    def _send_cut_windows(self, command: bytes) -> bool:
        """Envía comando de corte en Windows"""
        try:
            if not self.printer_name:
                logger.warning("No se especificó nombre de impresora para corte")
                return False
            
            import win32print
            printer_handle = win32print.OpenPrinter(self.printer_name)
            try:
                win32print.StartDocPrinter(printer_handle, 1, ("Cut Paper", None, "RAW"))
                win32print.StartPagePrinter(printer_handle)
                win32print.WritePrinter(printer_handle, command)
                win32print.EndPagePrinter(printer_handle)
                win32print.EndDocPrinter(printer_handle)
                logger.info(f"✅ Comando de corte enviado a {self.printer_name}")
                return True
            finally:
                win32print.ClosePrinter(printer_handle)
        except ImportError:
            logger.warning("pywin32 no está instalado. Intentando método alternativo...")
            try:
                printer_path = f"\\\\localhost\\{self.printer_name}"
                with open(printer_path, 'wb') as printer:
                    printer.write(command)
                logger.info(f"✅ Comando de corte enviado (método alternativo)")
                return True
            except Exception as e:
                logger.error(f"Error al enviar corte (método alternativo): {e}")
                return False
        except Exception as e:
            logger.error(f"Error al enviar corte en Windows: {e}")
            return False
    
    def _send_cut_macos(self, command: bytes) -> bool:
        """Envía comando de corte en macOS"""
        try:
            if not self.printer_name:
                result = subprocess.run(
                    ['lpstat', '-d'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    printer_name = result.stdout.split(':')[1].strip() if ':' in result.stdout else None
                else:
                    printer_name = None
            else:
                printer_name = self.printer_name
            
            if not printer_name:
                logger.warning("No se encontró impresora para enviar corte")
                return False
            
            # Guardar comando en archivo temporal
            temp_file = f"/tmp/cut_command_{datetime.now().timestamp()}.raw"
            with open(temp_file, 'wb') as f:
                f.write(command)
            
            # Enviar a impresora usando lpr
            result = subprocess.run(
                ['lpr', '-P', printer_name, '-o', 'raw', temp_file],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Limpiar archivo temporal
            try:
                os.remove(temp_file)
            except:
                pass
            
            if result.returncode == 0:
                logger.info(f"✅ Comando de corte enviado a {printer_name}")
                return True
            else:
                logger.error(f"Error al enviar corte: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error al enviar corte en macOS: {e}")
            return False
    
    def generate_guardarropia_ticket(
        self,
        ticket_code: str,
        customer_name: str,
        customer_phone: str,
        description: Optional[str] = None,
        price: float = 500.0,
        payment_type: str = "cash",
        deposited_at: Optional[str] = None
    ) -> Image.Image:
        """
        Genera imagen del ticket de guardarropía con código QR
        
        Args:
            ticket_code: Código único del ticket
            customer_name: Nombre del cliente
            customer_phone: Teléfono del cliente
            description: Descripción de la prenda (opcional)
            price: Precio pagado
            payment_type: Tipo de pago
            deposited_at: Fecha de depósito
            
        Returns:
            PIL Image del ticket
        """
        # Configuración para impresora térmica 80mm
        width = 384
        margin = 15
        line_height = 22
        font_size = 13
        
        # Calcular altura
        header_height = 50
        info_height = 120
        qr_height = 180
        footer_height = 40
        total_height = header_height + info_height + qr_height + footer_height + (margin * 2) + 20
        
        img = Image.new('RGB', (width, total_height), 'white')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
            font_bold = ImageFont.truetype("/System/Library/Fonts/Helvetica-Bold.ttc", font_size + 4)
            font_small = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size - 2)
        except:
            font = ImageFont.load_default()
            font_bold = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        y = margin
        
        # Encabezado
        draw.text((width // 2, y), "BIMBA", fill='black', font=font_bold, anchor='mm')
        y += line_height + 5
        draw.text((width // 2, y), "GUARDARROPÍA", fill='black', font=font_bold, anchor='mm')
        y += line_height + 15
        
        # Información del cliente
        draw.text((margin, y), f"Cliente: {customer_name[:30]}", fill='black', font=font)
        y += line_height
        draw.text((margin, y), f"Teléfono: {customer_phone[:30]}", fill='black', font=font)
        y += line_height
        
        if description:
            draw.text((margin, y), f"Prenda: {description[:30]}", fill='black', font=font)
            y += line_height
        
        # Línea separadora
        y += 5
        draw.line([(margin, y), (width - margin, y)], fill='black', width=1)
        y += line_height + 5
        
        # Precio y pago
        draw.text((margin, y), f"Precio: ${price:,.0f}", fill='black', font=font_bold)
        y += line_height
        payment_text = {
            'cash': 'Efectivo',
            'debit': 'Débito',
            'credit': 'Crédito'
        }.get(payment_type, payment_type)
        draw.text((margin, y), f"Pago: {payment_text}", fill='black', font=font)
        y += line_height + 10
        
        # Código QR
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=4,
                border=2
            )
            qr.add_data(ticket_code)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="black", back_color="white")
            qr_size = min(160, width - (margin * 2))
            qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
            
            x_pos = (width - qr_size) // 2
            img.paste(qr_img, (x_pos, y))
            y += qr_size + 10
            
            # Código de ticket en grande
            draw.text((width // 2, y), ticket_code, fill='black', font=font_bold, anchor='mm')
            y += line_height + 5
            
            # Instrucciones
            draw.text((width // 2, y), "Presente este código QR", fill='black', font=font_small, anchor='mm')
            y += line_height - 5
            draw.text((width // 2, y), "para retirar su prenda", fill='black', font=font_small, anchor='mm')
            
        except Exception as e:
            logger.error(f"Error al generar QR: {e}")
            # Si falla, solo mostrar el código
            draw.text((width // 2, y), ticket_code, fill='black', font=font_bold, anchor='mm')
        
        # Fecha
        if deposited_at:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(deposited_at.replace('Z', '+00:00'))
                date_str = dt.strftime('%d/%m/%Y %H:%M')
            except:
                date_str = deposited_at[:16]
            draw.text((width // 2, y + line_height + 10), date_str, fill='black', font=font_small, anchor='mm')
        
        return img
    
    def _send_cut_linux(self, command: bytes) -> bool:
        """Envía comando de corte en Linux"""
        try:
            if not self.printer_name:
                result = subprocess.run(
                    ['lpstat', '-d'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    printer_name = result.stdout.split(':')[1].strip() if ':' in result.stdout else None
                else:
                    printer_name = None
            else:
                printer_name = self.printer_name
            
            if not printer_name:
                logger.warning("No se encontró impresora para enviar corte")
                return False
            
            # Guardar comando en archivo temporal
            temp_file = f"/tmp/cut_command_{datetime.now().timestamp()}.raw"
            with open(temp_file, 'wb') as f:
                f.write(command)
            
            # Enviar a impresora usando lpr
            result = subprocess.run(
                ['lpr', '-P', printer_name, '-o', 'raw', temp_file],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Limpiar archivo temporal
            try:
                os.remove(temp_file)
            except:
                pass
            
            if result.returncode == 0:
                logger.info(f"✅ Comando de corte enviado a {printer_name}")
                return True
            else:
                logger.error(f"Error al enviar corte: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error al enviar corte en Linux: {e}")
            return False

