#!/bin/bash

# =============================================================================
# FinBot Enterprise - Load Test Runner
# Автоматизированный скрипт для нагрузочного тестирования
# =============================================================================

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Конфигурация
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$PROJECT_ROOT/load_test_results/$(date +%Y%m%d_%H%M%S)"
LOCUST_FILE="$PROJECT_ROOT/tests/load/locustfile.py"
K6_SCRIPT="$PROJECT_ROOT/tests/load/k6_test.js"

# Параметры по умолчанию
DURATION="5m"
USERS=100
RAMP_UP="30s"
SCENARIO="normal"

# Логирование
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Создание директории результатов
mkdir -p "$RESULTS_DIR"

# Проверка зависимостей
check_dependencies() {
    log_info "Проверка зависимостей..."
    
    if ! command -v locust &> /dev/null; then
        log_error "Locust не установлен. Установка: pip install locust"
        exit 1
    fi
    
    if ! command -v k6 &> /dev/null; then
        log_warning "k6 не установлен. Пропускаем k6 тесты."
        K6_AVAILABLE=false
    else
        K6_AVAILABLE=true
    fi
    
    if ! command -v docker &> /dev/null; then
        log_warning "Docker не доступен. Некоторые тесты могут быть недоступны."
    fi
    
    log_success "Зависимости проверены"
}

# Запуск Locust тестов
run_locust_test() {
    local scenario=$1
    local users=$2
    local duration=$3
    local ramp_up=$4
    
    log_info "Запуск Locust теста: сценарий=$scenario, пользователи=$users, длительность=$duration"
    
    case $scenario in
        normal)
            HEADLESS_ARGS="--headless -u $users -r 10 -t $duration"
            ;;
        peak)
            HEADLESS_ARGS="--headless -u 1000 -r 50 -t 30m"
            ;;
        stress)
            HEADLESS_ARGS="--headless -u 5000 -r 100 -t 15m"
            ;;
        soak)
            HEADLESS_ARGS="--headless -u 500 -r 20 -t 24h"
            ;;
        *)
            log_error "Неизвестный сценарий: $scenario"
            exit 1
            ;;
    esac
    
    # Запуск Locust
    locust -f "$LOCUST_FILE" $HEADLESS_ARGS \
        --csv="$RESULTS_DIR/locust_$scenario" \
        --html="$RESULTS_DIR/locust_$scenario.html" \
        --json="$RESULTS_DIR/locust_$scenario.json" \
        2>&1 | tee "$RESULTS_DIR/locust_$scenario.log"
    
    log_success "Locust тест завершен. Результаты: $RESULTS_DIR"
}

# Запуск k6 тестов
run_k6_test() {
    local scenario=$1
    
    if [ "$K6_AVAILABLE" = false ]; then
        log_warning "k6 не доступен, пропускаем k6 тест"
        return
    fi
    
    log_info "Запуск k6 теста: сценарий=$scenario"
    
    case $scenario in
        normal)
            K6_ARGS="--vus 100 --duration 5m"
            ;;
        peak)
            K6_ARGS="--vus 1000 --duration 30m"
            ;;
        stress)
            K6_ARGS="--vus 5000 --duration 15m"
            ;;
        soak)
            K6_ARGS="--vus 500 --duration 24h"
            ;;
    esac
    
    k6 run $K6_ARGS "$K6_SCRIPT" \
        --out json="$RESULTS_DIR/k6_$scenario.json" \
        --out csv="$RESULTS_DIR/k6_$scenario.csv" \
        2>&1 | tee "$RESULTS_DIR/k6_$scenario.log"
    
    log_success "k6 тест завершен"
}

# Генерация отчета
generate_report() {
    log_info "Генерация отчета..."
    
    cat > "$RESULTS_DIR/REPORT.md" << EOF
# Отчет о Нагрузочном Тестировании

**Дата**: $(date +"%Y-%m-%d %H:%M:%S")  
**Сценарий**: $SCENARIO  
**Пользователей**: $USERS  
**Длительность**: $DURATION  

## Результаты Locust

- HTML отчет: [locust_${SCENARIO}.html](locust_${SCENARIO}.html)
- JSON данные: [locust_${SCENARIO}.json](locust_${SCENARIO}.json)
- CSV данные: [locust_${SCENARIO}_requests.csv](locust_${SCENARIO}_requests.csv)

## Результаты k6

- JSON данные: [k6_${SCENARIO}.json](k6_${SCENARIO}.json)
- CSV данные: [k6_${SCENARIO}.csv](k6_${SCENARIO}.csv)

## Метрики

### Производительность
- Средний RPS: TBD (анализ данных)
- P95 Latency: TBD
- P99 Latency: TBD
- Ошибки: TBD

### Ресурсы
- CPU Usage: TBD
- Memory Usage: TBD
- Network I/O: TBD

## Рекомендации

TBD (после анализа данных)

EOF
    
    log_success "Отчет сгенерирован: $RESULTS_DIR/REPORT.md"
}

# Мониторинг ресурсов
monitor_resources() {
    log_info "Запуск мониторинга ресурсов..."
    
    # Docker stats
    if command -v docker &> /dev/null; then
        docker stats --no-stream > "$RESULTS_DIR/docker_stats.txt" 2>&1 &
        DOCKER_STATS_PID=$!
        trap "kill $DOCKER_STATS_PID 2>/dev/null" EXIT
    fi
    
    # System metrics
    (
        while true; do
            echo "=== $(date) ===" >> "$RESULTS_DIR/system_metrics.log"
            echo "CPU: $(top -bn1 | grep 'Cpu(s)' | awk '{print $2}')%" >> "$RESULTS_DIR/system_metrics.log"
            echo "Memory: $(free -h | grep Mem | awk '{print $3/$2 * 100.0}')%" >> "$RESULTS_DIR/system_metrics.log"
            if command -v nvidia-smi &> /dev/null; then
                nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv >> "$RESULTS_DIR/system_metrics.log"
            fi
            sleep 10
        done
    ) &
    MONITOR_PID=$!
    trap "kill $MONITOR_PID 2>/dev/null" EXIT
    
    log_success "Мониторинг запущен"
}

# Основная функция
main() {
    echo "=============================================="
    echo "  FinBot Enterprise - Load Test Runner"
    echo "=============================================="
    echo ""
    
    check_dependencies
    monitor_resources
    
    log_info "Начало тестирования..."
    run_locust_test "$SCENARIO" "$USERS" "$DURATION" "$RAMP_UP"
    run_k6_test "$SCENARIO"
    generate_report
    
    echo ""
    echo "=============================================="
    log_success "Тестирование завершено!"
    echo "Результаты сохранены в: $RESULTS_DIR"
    echo "=============================================="
}

# Парсинг аргументов
while [[ $# -gt 0 ]]; do
    case $1 in
        -s|--scenario)
            SCENARIO="$2"
            shift 2
            ;;
        -u|--users)
            USERS="$2"
            shift 2
            ;;
        -d|--duration)
            DURATION="$2"
            shift 2
            ;;
        -r|--ramp-up)
            RAMP_UP="$2"
            shift 2
            ;;
        -h|--help)
            echo "Использование: $0 [OPTIONS]"
            echo ""
            echo "Опции:"
            echo "  -s, --scenario SCENARIO   Сценарий теста (normal, peak, stress, soak)"
            echo "  -u, --users USERS         Количество пользователей (по умолчанию: 100)"
            echo "  -d, --duration DURATION   Длительность теста (по умолчанию: 5m)"
            echo "  -r, --ramp-up RAMP_UP     Время нарастания нагрузки (по умолчанию: 30s)"
            echo "  -h, --help                Показать эту справку"
            echo ""
            echo "Примеры:"
            echo "  $0 --scenario normal --users 100 --duration 5m"
            echo "  $0 -s peak -u 1000 -d 30m"
            echo "  $0 -s stress -u 5000 -d 15m"
            exit 0
            ;;
        *)
            log_error "Неизвестная опция: $1"
            exit 1
            ;;
    esac
done

main
