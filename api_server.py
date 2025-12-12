#!/usr/bin/env python3
"""
REST API сервер для управления парсером SteamCharts
Endpoints:
- POST /start - запуск парсера с файлом app_ids
- GET /status - статус парсинга
- POST /stop - остановка парсера
- GET /export - экспорт результатов
"""
import os
import json
import threading
import logging
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename
import config
from parser import SteamDBParser
from itad_parser_main import ITADParserMain

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['UPLOAD_FOLDER'] = config.DATA_DIR

# Глобальное состояние парсера
parser_instance = None
parser_thread = None
parser_running = False

# Глобальное состояние ITAD парсера
itad_parser_instance = None
itad_parser_thread = None
itad_parser_running = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_parser_in_thread(app_ids_file: Path):
    """Запуск парсера в отдельном потоке"""
    global parser_instance, parser_running
    
    try:
        parser_running = True
        logger.info(f"Starting parser with app_ids file: {app_ids_file}")
        
        # Копируем файл в стандартное место или используем напрямую
        # Временно заменяем APP_IDS_FILE в config
        original_file = config.APP_IDS_FILE
        
        # Копируем загруженный файл в стандартное место
        # Преобразуем Path в строки для shutil.copy2
        import shutil
        source_path = str(app_ids_file) if isinstance(app_ids_file, Path) else app_ids_file
        dest_path = str(config.APP_IDS_FILE) if isinstance(config.APP_IDS_FILE, Path) else config.APP_IDS_FILE
        shutil.copy2(source_path, dest_path)
        logger.info(f"Copied {source_path} to {dest_path}")
        
        parser_instance = SteamDBParser(data_source='steamcharts')
        parser_instance.run()
        
        logger.info("Parser completed successfully")
    except Exception as e:
        logger.error(f"Parser error: {e}", exc_info=True)
    finally:
        parser_running = False
        parser_instance = None


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    try:
        # Проверяем подключение к БД
        from database import Database
        db = Database()
        db_ok = db.use_postgresql or db.db_path.exists()
        db.close()
        
        return jsonify({
            'status': 'ok',
            'parser_running': parser_running,
            'database_connected': db_ok,
            'postgresql': config.USE_POSTGRESQL
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@app.route('/start', methods=['POST'])
def start_parser():
    """Запуск парсера с файлом app_ids"""
    global parser_thread, parser_running
    
    if parser_running:
        return jsonify({
            'error': 'Parser is already running',
            'status': 'running'
        }), 400
    
    # Проверяем наличие файла в запросе
    if 'file' not in request.files:
        return jsonify({
            'error': 'No file provided. Please upload app_ids.txt file'
        }), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            'error': 'No file selected'
        }), 400
    
    # Сохраняем файл
    # Убеждаемся, что filename - строка
    file_filename = file.filename if file.filename else 'app_ids.txt'
    if not isinstance(file_filename, str):
        file_filename = str(file_filename)
    filename = secure_filename(file_filename)
    upload_folder = Path(app.config['UPLOAD_FOLDER'])
    filepath = upload_folder / filename
    file.save(str(filepath))
    
    logger.info(f"Received app_ids file: {filename}, saved to {filepath}")
    
    # Проверяем формат файла
    try:
        with open(filepath, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
            if not lines:
                return jsonify({
                    'error': 'File is empty'
                }), 400
            
            # Проверяем, что это числа
            try:
                app_ids = [int(line) for line in lines if line.isdigit()]
                if not app_ids:
                    return jsonify({
                        'error': 'No valid app IDs found in file'
                    }), 400
            except ValueError:
                return jsonify({
                    'error': 'Invalid file format. Expected one app ID per line'
                }), 400
        
        logger.info(f"File validated: {len(app_ids)} app IDs found")
    except Exception as e:
        return jsonify({
            'error': f'Error reading file: {str(e)}'
        }), 400
    
    # Запускаем парсер в отдельном потоке
    parser_thread = threading.Thread(
        target=run_parser_in_thread,
        args=(filepath,),
        daemon=True
    )
    parser_thread.start()
    
    return jsonify({
        'status': 'started',
        'message': f'Parser started with {len(app_ids)} app IDs',
        'file': filename
    }), 200


@app.route('/status', methods=['GET'])
def status():
    """Получить статус парсинга"""
    try:
        # Получаем статистику из БД
        from database import Database
        db = Database()
        try:
            stats = db.get_statistics()
        finally:
            db.close()
        
        total = stats.get('total', 0)
        completed = stats.get('completed', 0)
        errors_count = stats.get('errors', 0)
        
        progress_percent = 0.0
        if total > 0:
            progress_percent = round((completed + errors_count) / total * 100, 2)
        
        return jsonify({
            'parser_running': parser_running,
            'statistics': {
                'total_apps': total,
                'completed': completed,
                'pending': stats.get('pending', 0),
                'errors': errors_count,
                'ccu_records': stats.get('ccu_records', 0),
                'price_records': stats.get('price_records', 0)
            },
            'progress_percent': progress_percent
        }), 200
    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'parser_running': parser_running
        }), 500


@app.route('/stop', methods=['POST'])
def stop_parser():
    """Остановка парсера"""
    global parser_instance, parser_running
    
    if not parser_running:
        return jsonify({
            'status': 'not_running',
            'message': 'Parser is not running'
        }), 200
    
    try:
        if parser_instance:
            parser_instance.running = False
            logger.info("Stopping parser...")
        
        parser_running = False
        
        return jsonify({
            'status': 'stopping',
            'message': 'Parser stop signal sent'
        }), 200
    except Exception as e:
        logger.error(f"Error stopping parser: {e}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/export', methods=['GET'])
def export_data():
    """Экспорт результатов парсинга"""
    try:
        export_type = request.args.get('type', 'full')  # 'full', 'ccu', 'errors'
        
        from database import Database
        from export_steamcharts_csv import export_to_csv
        from export_errors import export_errors_to_csv
        from pathlib import Path
        from datetime import datetime
        
        db = Database()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export_type == 'ccu':
            output_file = config.DATA_DIR / f"ccu_export_{timestamp}.csv"
            try:
                export_to_csv(db, output_file)
                if not output_file.exists():
                    return jsonify({'error': 'Export file not created'}), 500
                return send_file(str(output_file), as_attachment=True, download_name=f"ccu_export_{timestamp}.csv")
            finally:
                db.close()
        
        elif export_type == 'errors':
            output_file = config.DATA_DIR / f"errors_export_{timestamp}.csv"
            try:
                count = export_errors_to_csv(db, output_file)
                if count == 0:
                    return jsonify({'message': 'No errors to export'}), 200
                if not output_file.exists():
                    return jsonify({'error': 'Export file not created'}), 500
                return send_file(str(output_file), as_attachment=True, download_name=f"errors_export_{timestamp}.csv")
            finally:
                db.close()
        
        else:  # full
            # Экспортируем оба файла в архив или возвращаем JSON с путями
            ccu_file = config.DATA_DIR / f"ccu_export_{timestamp}.csv"
            errors_file = config.DATA_DIR / f"errors_export_{timestamp}.csv"
            
            try:
                export_to_csv(db, ccu_file)
                export_errors_to_csv(db, errors_file)
                
                return jsonify({
                    'status': 'exported',
                    'files': {
                        'ccu': f"/download/ccu?timestamp={timestamp}",
                        'errors': f"/download/errors?timestamp={timestamp}"
                    },
                    'message': 'Export completed. Use /download endpoints to get files.'
                }), 200
            finally:
                db.close()
        
    except Exception as e:
        logger.error(f"Error exporting data: {e}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/download/<file_type>', methods=['GET'])
def download_file(file_type):
    """Скачивание экспортированных файлов"""
    timestamp = request.args.get('timestamp')
    
    if file_type == 'ccu':
        filename = f"ccu_export_{timestamp}.csv" if timestamp else "ccu_export_latest.csv"
    elif file_type == 'errors':
        filename = f"errors_export_{timestamp}.csv" if timestamp else "errors_export_latest.csv"
    else:
        return jsonify({'error': 'Invalid file type'}), 400
    
    filepath = config.DATA_DIR / filename
    
    if not filepath.exists():
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(str(filepath), as_attachment=True, download_name=filename)


@app.route('/logs', methods=['GET'])
def get_logs():
    """Получить последние логи парсера"""
    lines = request.args.get('lines', 100, type=int)
    
    log_file = config.LOG_FILE
    if not log_file.exists():
        return jsonify({
            'logs': [],
            'message': 'Log file not found'
        }), 200
    
    try:
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        return jsonify({
            'logs': [line.strip() for line in recent_lines],
            'total_lines': len(all_lines)
        }), 200
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


def run_itad_parser_in_thread(app_ids_file: Path):
    """Запуск ITAD парсера в отдельном потоке"""
    global itad_parser_instance, itad_parser_running
    
    try:
        itad_parser_running = True
        logger.info(f"Starting ITAD parser with app_ids file: {app_ids_file}")
        
        # Копируем файл в стандартное место
        import shutil
        source_path = str(app_ids_file) if isinstance(app_ids_file, Path) else app_ids_file
        dest_path = str(config.APP_IDS_FILE) if isinstance(config.APP_IDS_FILE, Path) else config.APP_IDS_FILE
        shutil.copy2(source_path, dest_path)
        logger.info(f"Copied {source_path} to {dest_path}")
        
        itad_parser_instance = ITADParserMain(app_ids_file=Path(dest_path))
        itad_parser_instance.run()
        
        logger.info("ITAD parser completed successfully")
    except Exception as e:
        logger.error(f"ITAD parser error: {e}", exc_info=True)
    finally:
        itad_parser_running = False
        itad_parser_instance = None


@app.route('/itad/start', methods=['POST'])
def start_itad_parser():
    """Запуск ITAD парсера с файлом app_ids"""
    global itad_parser_thread, itad_parser_running
    
    if itad_parser_running:
        return jsonify({
            'error': 'ITAD parser is already running',
            'status': 'running'
        }), 400
    
    # Проверяем наличие файла в запросе
    if 'file' not in request.files:
        return jsonify({
            'error': 'No file provided. Please upload app_ids.txt file'
        }), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({
            'error': 'No file selected'
        }), 400
    
    # Сохраняем файл
    file_filename = file.filename if file.filename else 'app_ids.txt'
    if not isinstance(file_filename, str):
        file_filename = str(file_filename)
    filename = secure_filename(file_filename)
    upload_folder = Path(app.config['UPLOAD_FOLDER'])
    filepath = upload_folder / filename
    file.save(str(filepath))
    
    logger.info(f"Received app_ids file for ITAD parser: {filename}, saved to {filepath}")
    
    # Проверяем формат файла
    try:
        with open(filepath, 'r') as f:
            lines = [line.strip() for line in f if line.strip()]
            if not lines:
                return jsonify({
                    'error': 'File is empty'
                }), 400
            
            # Проверяем, что это числа
            try:
                app_ids = [int(line) for line in lines if line.isdigit()]
                if not app_ids:
                    return jsonify({
                        'error': 'No valid app IDs found in file'
                    }), 400
            except ValueError:
                return jsonify({
                    'error': 'Invalid file format. Expected one app ID per line'
                }), 400
        
        logger.info(f"File validated: {len(app_ids)} app IDs found")
    except Exception as e:
        return jsonify({
            'error': f'Error reading file: {str(e)}'
        }), 400
    
    # Запускаем ITAD парсер в отдельном потоке
    itad_parser_thread = threading.Thread(
        target=run_itad_parser_in_thread,
        args=(filepath,),
        daemon=True
    )
    itad_parser_thread.start()
    
    return jsonify({
        'status': 'started',
        'message': f'ITAD parser started with {len(app_ids)} app IDs',
        'file': filename
    }), 200


@app.route('/itad/status', methods=['GET'])
def itad_status():
    """Получить статус ITAD парсинга"""
    try:
        # Получаем статистику из БД
        from database import Database
        db = Database()
        try:
            stats = db.get_statistics()
            
            # Получаем ITAD-специфичную статистику
            cursor = db._get_cursor()
            if db.use_postgresql:
                cursor.execute("""
                    SELECT 
                        COUNT(*) FILTER (WHERE status = 'itad_completed') as completed,
                        COUNT(*) FILTER (WHERE status = 'itad_processing') as processing,
                        COUNT(*) FILTER (WHERE status = 'itad_error') as errors,
                        SUM(itad_price_processed) as total_price_records
                    FROM app_status
                """)
            else:
                cursor.execute("""
                    SELECT 
                        SUM(CASE WHEN status = 'itad_completed' THEN 1 ELSE 0 END) as completed,
                        SUM(CASE WHEN status = 'itad_processing' THEN 1 ELSE 0 END) as processing,
                        SUM(CASE WHEN status = 'itad_error' THEN 1 ELSE 0 END) as errors,
                        SUM(itad_price_processed) as total_price_records
                    FROM app_status
                """)
            
            row = cursor.fetchone()
            itad_stats = {
                'completed': row[0] or 0,
                'processing': row[1] or 0,
                'errors': row[2] or 0,
                'total_price_records': row[3] or 0
            }
            
        finally:
            db.close()
        
        total = stats.get('total', 0)
        completed = itad_stats['completed']
        errors_count = itad_stats['errors']
        
        progress_percent = 0.0
        if total > 0:
            progress_percent = round((completed + errors_count) / total * 100, 2)
        
        return jsonify({
            'parser_running': itad_parser_running,
            'statistics': {
                'total_apps': total,
                'completed': completed,
                'processing': itad_stats['processing'],
                'pending': stats.get('pending', 0),
                'errors': errors_count,
                'price_records': itad_stats['total_price_records']
            },
            'progress_percent': progress_percent
        }), 200
    except Exception as e:
        logger.error(f"Error getting ITAD status: {e}", exc_info=True)
        return jsonify({
            'error': str(e),
            'parser_running': itad_parser_running
        }), 500


@app.route('/itad/stop', methods=['POST'])
def stop_itad_parser():
    """Остановка ITAD парсера"""
    global itad_parser_instance, itad_parser_running
    
    if not itad_parser_running:
        return jsonify({
            'status': 'not_running',
            'message': 'ITAD parser is not running'
        }), 200
    
    try:
        if itad_parser_instance:
            itad_parser_instance.running = False
            # Safely stop parser if it exists
            if hasattr(itad_parser_instance, 'parser'):
                itad_parser_instance.parser.running = False
            logger.info("Stopping ITAD parser...")
        
        itad_parser_running = False
        
        return jsonify({
            'status': 'stopping',
            'message': 'ITAD parser stop signal sent'
        }), 200
    except Exception as e:
        logger.error(f"Error stopping ITAD parser: {e}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/itad/export', methods=['GET'])
def export_itad_data():
    """Экспорт ITAD результатов в CSV"""
    try:
        from database import Database
        from pathlib import Path
        from datetime import datetime
        import csv
        
        db = Database()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = config.DATA_DIR / f"itad_price_history_export_{timestamp}.csv"
        
        try:
            cursor = db._get_cursor()
            
            # Export price_history data
            if db.use_postgresql:
                cursor.execute("""
                    SELECT app_id, datetime, price_final, currency_symbol, currency_name
                    FROM price_history
                    ORDER BY app_id, datetime
                """)
            else:
                cursor.execute("""
                    SELECT app_id, datetime, price_final, currency_symbol, currency_name
                    FROM price_history
                    ORDER BY app_id, datetime
                """)
            
            rows = cursor.fetchall()
            
            # Write to CSV
            with open(output_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['app_id', 'datetime', 'price_final', 'currency_symbol', 'currency_name'])
                writer.writerows(rows)
            
            logger.info(f"Exported {len(rows)} ITAD price records to {output_file}")
            
            if not output_file.exists():
                return jsonify({'error': 'Export file not created'}), 500
            
            return send_file(str(output_file), as_attachment=True, download_name=f"itad_price_history_{timestamp}.csv")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error exporting ITAD data: {e}", exc_info=True)
        return jsonify({
            'error': str(e)
        }), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    host = os.getenv('HOST', '0.0.0.0')
    
    logger.info(f"Starting API server on {host}:{port}")
    logger.info(f"Database: PostgreSQL={config.USE_POSTGRESQL}, URL={'set' if config.DATABASE_URL else 'not set'}")
    
    # Flask development server (для production используется gunicorn через Procfile)
    app.run(host=host, port=port, debug=False, threaded=True)
