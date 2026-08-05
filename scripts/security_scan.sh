#!/bin/bash

# =============================================================================
# FinBot Enterprise - Security Scan Script
# Полный аудит безопасности проекта
# =============================================================================

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Конфигурация
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RESULTS_DIR="$PROJECT_ROOT/security_audit/$(date +%Y%m%d_%H%M%S)"
REPORT_FILE="$RESULTS_DIR/SECURITY_AUDIT_REPORT.md"

# Логирование
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠ WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
}

log_section() {
    echo -e "\n${MAGENTA}========================================${NC}"
    echo -e "${MAGENTA}$1${NC}"
    echo -e "${MAGENTA}========================================${NC}\n"
}

# Создание директории результатов
mkdir -p "$RESULTS_DIR"

# Инициализация отчета
init_report() {
    cat > "$REPORT_FILE" << EOF
# Отчет об Аудите Безопасности FinBot Enterprise

**Дата**: $(date +"%Y-%m-%d %H:%M:%S")  
**Версия**: 1.0  
**Аудитор**: Automated Security Scanner  

## Executive Summary

| Категория | Статус | Критические | Высокие | Средние | Низкие |
|-----------|--------|-------------|---------|---------|--------|
| Код и Зависимости | TBD | 0 | 0 | 0 | 0 |
| Инфраструктура | TBD | 0 | 0 | 0 | 0 |
| Приложение | TBD | 0 | 0 | 0 | 0 |
| Данные и Приватность | TBD | 0 | 0 | 0 | 0 |

**Общий уровень риска**: TBD

---

## Детальные Результаты

EOF
}

# Проверка зависимостей
check_dependencies() {
    log_section "Проверка зависимостей"
    
    DEPS_OK=true
    
    # Python пакеты
    if ! command -v bandit &> /dev/null; then
        log_warning "bandit не установлен (pip install bandit)"
        DEPS_OK=false
    fi
    
    if ! command -v safety &> /dev/null; then
        log_warning "safety не установлен (pip install safety)"
        DEPS_OK=false
    fi
    
    # Docker инструменты
    if ! command -v trivy &> /dev/null; then
        log_warning "trivy не установлен"
    fi
    
    # Node.js инструменты
    if ! command -v npm &> /dev/null; then
        log_warning "npm не доступен, пропускаем проверку JS зависимостей"
    fi
    
    if [ "$DEPS_OK" = true ]; then
        log_success "Все основные зависимости установлены"
    else
        log_info "Некоторые инструменты отсутствуют, проверка будет неполной"
    fi
}

# Статический анализ кода (SAST)
run_sast() {
    log_section "Статический анализ кода (SAST)"
    
    log_info "Запуск bandit (Python security linter)..."
    
    if command -v bandit &> /dev/null; then
        bandit -r "$PROJECT_ROOT/app" -f html -o "$RESULTS_DIR/bandit_report.html" 2>&1 | tee "$RESULTS_DIR/bandit_output.txt" || true
        bandit -r "$PROJECT_ROOT/app" -f json -o "$RESULTS_DIR/bandit_report.json" 2>&1 || true
        
        # Подсчет уязвимостей
        HIGH_COUNT=$(grep -c '"severity": "HIGH"' "$RESULTS_DIR/bandit_report.json" 2>/dev/null || echo "0")
        MEDIUM_COUNT=$(grep -c '"severity": "MEDIUM"' "$RESULTS_DIR/bandit_report.json" 2>/dev/null || echo "0")
        LOW_COUNT=$(grep -c '"severity": "LOW"' "$RESULTS_DIR/bandit_report.json" 2>/dev/null || echo "0")
        
        if [ "$HIGH_COUNT" -eq 0 ] && [ "$MEDIUM_COUNT" -eq 0 ]; then
            log_success "Bandit: Критических и высоких уязвимостей не найдено"
        else
            log_error "Bandit: Найдено уязвимостей - HIGH: $HIGH_COUNT, MEDIUM: $MEDIUM_COUNT, LOW: $LOW_COUNT"
        fi
        
        # Добавление в отчет
        cat >> "$REPORT_FILE" << EOF

### Статический анализ (Bandit)

- **Высокие уязвимости**: $HIGH_COUNT
- **Средние уязвимости**: $MEDIUM_COUNT
- **Низкие уязвимости**: $LOW_COUNT
- **Отчет**: [bandit_report.html](bandit_report.html)

EOF
    else
        log_warning "Bandit не установлен, пропускаем"
    fi
}

# Анализ зависимостей (SCA)
run_sca() {
    log_section "Анализ зависимостей (SCA)"
    
    log_info "Проверка Python зависимостей..."
    
    if command -v safety &> /dev/null; then
        safety check --json > "$RESULTS_DIR/safety_report.json" 2>&1 || true
        safety check > "$RESULTS_DIR/safety_output.txt" 2>&1 || true
        
        VULN_COUNT=$(grep -c "vulnerability" "$RESULTS_DIR/safety_report.json" 2>/dev/null || echo "0")
        
        if [ "$VULN_COUNT" -eq 0 ]; then
            log_success "Safety: Уязвимостей в зависимостях не найдено"
        else
            log_error "Safety: Найдено уязвимостей: $VULN_COUNT"
        fi
        
        cat >> "$REPORT_FILE" << EOF

### Анализ зависимостей (Safety)

- **Найдено уязвимостей**: $VULN_COUNT
- **Отчет**: [safety_report.json](safety_report.json)

EOF
    else
        log_warning "Safety не установлен, пропускаем"
    fi
    
    # Проверка через pip-audit
    if command -v pip-audit &> /dev/null; then
        log_info "Запуск pip-audit..."
        pip-audit --format json > "$RESULTS_DIR/pip_audit_report.json" 2>&1 || true
    fi
    
    # Node.js зависимости
    if command -v npm &> /dev/null && [ -f "$PROJECT_ROOT/package.json" ]; then
        log_info "Проверка Node.js зависимостей..."
        cd "$PROJECT_ROOT"
        npm audit --json > "$RESULTS_DIR/npm_audit.json" 2>&1 || true
    fi
}

# Проверка секретов в коде
scan_secrets() {
    log_section "Поиск секретов в коде"
    
    log_info "Запуск поиска API ключей и паролей..."
    
    # Простой grep поиск паттернов
    PATTERNS=(
        "api_key\s*=\s*['\"][^'\"]+['\"]"
        "password\s*=\s*['\"][^'\"]+['\"]"
        "secret\s*=\s*['\"][^'\"]+['\"]"
        "token\s*=\s*['\"][^'\"]+['\"]"
        "AWS_SECRET_ACCESS_KEY"
        "PRIVATE_KEY"
    )
    
    FOUND_SECRETS=0
    
    for pattern in "${PATTERNS[@]}"; do
        MATCHES=$(grep -r --include="*.py" --include="*.js" --include="*.env*" -E "$pattern" "$PROJECT_ROOT" 2>/dev/null | grep -v ".git" | wc -l || echo "0")
        if [ "$MATCHES" -gt 0 ]; then
            log_warning "Найдено совпадений для паттерна '$pattern': $MATCHES"
            FOUND_SECRETS=$((FOUND_SECRETS + MATCHES))
        fi
    done
    
    if [ "$FOUND_SECRETS" -eq 0 ]; then
        log_success "Очевидных секретов в коде не найдено"
    else
        log_error "Возможные секреты найдены: $FOUND_SECRETS"
    fi
    
    cat >> "$REPORT_FILE" << EOF

### Поиск секретов

- **Найдено потенциальных секретов**: $FOUND_SECRETS
- **Рекомендация**: Используйте переменные окружения или secrets manager

EOF
    
    # Если установлен gitLeaks
    if command -v gitleaks &> /dev/null; then
        log_info "Запуск gitleaks..."
        gitleaks detect --source "$PROJECT_ROOT" --report-path "$RESULTS_DIR/gitleaks_report.json" 2>&1 || true
    fi
}

# Проверка Docker образов
scan_docker() {
    log_section "Сканирование Docker образов"
    
    if ! command -v docker &> /dev/null; then
        log_warning "Docker не доступен, пропускаем"
        return
    fi
    
    if command -v trivy &> /dev/null; then
        log_info "Сканирование образа bot с помощью trivy..."
        
        # Сначала пробуем собрать образ
        if docker images finbot:latest -q | grep -q .; then
            trivy image finbot:latest --format json --output "$RESULTS_DIR/trivy_image_report.json" 2>&1 || true
            trivy image finbot:latest 2>&1 | tee "$RESULTS_DIR/trivy_output.txt" || true
            
            CRITICAL=$(grep -c '"Severity": "CRITICAL"' "$RESULTS_DIR/trivy_image_report.json" 2>/dev/null || echo "0")
            HIGH=$(grep -c '"Severity": "HIGH"' "$RESULTS_DIR/trivy_image_report.json" 2>/dev/null || echo "0")
            
            if [ "$CRITICAL" -eq 0 ] && [ "$HIGH" -eq 0 ]; then
                log_success "Trivy: Критических и высоких уязвимостей в образе не найдено"
            else
                log_error "Trivy: Найдено уязвимостей - CRITICAL: $CRITICAL, HIGH: $HIGH"
            fi
        else
            log_warning "Образ finbot:latest не найден. Сначала выполните docker-compose build"
        fi
    else
        log_warning "trivy не установлен, пропускаем сканирование образов"
    fi
}

# Проверка конфигурации K8s
scan_k8s_config() {
    log_section "Проверка конфигурации Kubernetes"
    
    K8S_DIR="$PROJECT_ROOT/k8s"
    
    if [ ! -d "$K8S_DIR" ]; then
        log_warning "Директория k8s не найдена, пропускаем"
        return
    fi
    
    # Проверка на наличие securityContext
    if grep -r "securityContext" "$K8S_DIR" > /dev/null 2>&1; then
        log_success "securityContext найден в манифестах K8s"
    else
        log_warning "securityContext не найден в манифестах K8s"
    fi
    
    # Проверка на hardcoded секреты
    if grep -r "password:" "$K8S_DIR" | grep -v "Secret" | grep -v "#" > /dev/null 2>&1; then
        log_error "Возможные hardcoded пароли в K8s манифестах"
    else
        log_success "Hardcoded пароли в K8s манифестах не найдены"
    fi
    
    # Если установлен kube-bench
    if command -v kube-bench &> /dev/null; then
        log_info "Запуск kube-bench..."
        kube-bench --json > "$RESULTS_DIR/kube_bench_report.json" 2>&1 || true
    fi
}

# Проверка OWASP Top 10
check_owasp_top10() {
    log_section "Проверка OWASP Top 10"
    
    log_info "Проверка на распространенные уязвимости..."
    
    ISSUES_FOUND=0
    
    # A01: Broken Access Control
    if grep -r "@app.route" "$PROJECT_ROOT/app" | grep -v "login_required" > /dev/null 2>&1; then
        log_warning "Возможные проблемы с контролем доступа (A01)"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        log_success "Контроль доступа реализован корректно (A01)"
    fi
    
    # A03: Injection
    if grep -r "execute(" "$PROJECT_ROOT/app" | grep -v "parameterized" > /dev/null 2>&1; then
        log_warning "Возможные SQL injection (A03)"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        log_success "SQL injection защищены (A03)"
    fi
    
    # A05: Security Misconfiguration
    if grep -r "DEBUG\s*=\s*True" "$PROJECT_ROOT/app" > /dev/null 2>&1; DEBUG_MODE=$(grep -r "DEBUG" "$PROJECT_ROOT/app/config" 2>/dev/null | grep -i true); then
        log_warning "Debug режим включен (A05)"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        log_success "Debug режим отключен (A05)"
    fi
    
    # A07: XSS
    if grep -r "render_template_string" "$PROJECT_ROOT/app" | grep -v "escape" > /dev/null 2>&1; then
        log_warning "Возможные XSS уязвимости (A07)"
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
    else
        log_success "XSS защищены (A07)"
    fi
    
    cat >> "$REPORT_FILE" << EOF

### OWASP Top 10 Проверка

- **Найдено проблем**: $ISSUES_FOUND
- **Рекомендация**: Исправить все выявленные проблемы перед релизом

EOF
    
    if [ "$ISSUES_FOUND" -eq 0 ]; then
        log_success "OWASP Top 10: Критических проблем не найдено"
    else
        log_error "OWASP Top 10: Найдено проблем: $ISSUES_FOUND"
    fi
}

# Генерация финального отчета
finalize_report() {
    log_section "Генерация финального отчета"
    
    cat >> "$REPORT_FILE" << EOF

---

## Рекомендации

1. **Немедленные действия**:
   - Исправить все критические и высокие уязвимости
   - Обновить зависимости с известными уязвимостями
   - Удалить любые найденные секреты из кода

2. **Краткосрочные улучшения**:
   - Внедрить автоматическое сканирование в CI/CD
   - Настроить регулярные penetration тесты
   - Обучить команду безопасной разработке

3. **Долгосрочная стратегия**:
   - Получить сертификацию SOC2 Type II
   - Внедрить bug bounty программу
   - Проводить ежеквартальные аудиты безопасности

---

## Приложения

- [bandit_report.html](bandit_report.html) - Отчет статического анализа
- [bandit_report.json](bandit_report.json) - JSON версия отчета bandit
- [safety_report.json](safety_report.json) - Отчет анализа зависимостей
- [trivy_image_report.json](trivy_image_report.json) - Отчет сканирования Docker образа
- [gitleaks_report.json](gitleaks_report.json) - Отчет поиска секретов (если доступен)

---

*Отчет сгенерирован автоматически FinBot Enterprise Security Scanner*  
*Для вопросов обращайтесь: security@finbot.enterprise*

EOF
    
    log_success "Отчет сохранен: $REPORT_FILE"
}

# Основная функция
main() {
    echo -e "${BLUE}"
    echo "=============================================="
    echo "  FinBot Enterprise - Security Audit Tool"
    echo "=============================================="
    echo -e "${NC}"
    
    init_report
    check_dependencies
    run_sast
    run_sca
    scan_secrets
    scan_docker
    scan_k8s_config
    check_owasp_top10
    finalize_report
    
    echo ""
    echo -e "${GREEN}=============================================="
    echo "  Аудит безопасности завершен!"
    echo "==============================================${NC}"
    echo ""
    echo "Полный отчет: $REPORT_FILE"
    echo ""
}

# Запуск
main "$@"
