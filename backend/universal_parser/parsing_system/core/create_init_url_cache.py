from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def capture_html_for_rendering(url, selector=None, include_images=False):
    """
    Збирає HTML зі всіма вбудованими стилями для рендерингу на сторінці

    Args:
        url: URL сторінки для збору
        selector: CSS селектор конкретного блоку (None = вся сторінка)
        include_images: Чи конвертувати зображення в base64 (повільно!)

    Returns:
        str: HTML з вбудованими стилями
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-notifications')  # Вимикаємо сповіщення
    options.add_argument('--disable-popup-blocking')  # Але дозволяємо popup для обробки
    options.add_argument('--headless')

    driver = webdriver.Chrome(options=options)

    # Збільшуємо таймаут для асинхронних скриптів
    driver.set_script_timeout(120)  # 2 хвилини

    try:
        print("📡 Завантажуємо сторінку...")
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(3)
        print("✅ Сторінка завантажена")

        # Закриваємо popup-вікна
        close_popups(driver)
        time.sleep(1)  # Даємо час на закриття

        # Спочатку збираємо інформацію про CSS
        css_links = driver.execute_script("""
            return Array.from(document.querySelectorAll('link[rel="stylesheet"]'))
                .map(link => link.href);
        """)
        print(f"📋 Знайдено CSS файлів: {len(css_links)}")

        # JavaScript для вбудовування стилів (оптимізований)
        script = """
        async function captureHTMLWithStyles(selector, includeImages) {
            console.log('Починаємо збір стилів...');

            // Вбудовуємо всі CSS файли у <style> теги
            const links = Array.from(document.querySelectorAll('link[rel="stylesheet"]'));
            console.log('CSS файлів знайдено:', links.length);

            let processedCount = 0;

            for (let link of links) {
                try {
                    const controller = new AbortController();
                    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 сек на файл

                    const response = await fetch(link.href, { 
                        signal: controller.signal,
                        mode: 'cors',
                        credentials: 'omit'
                    });
                    clearTimeout(timeoutId);

                    const cssText = await response.text();

                    const styleTag = document.createElement('style');
                    styleTag.setAttribute('data-original-href', link.href);
                    styleTag.textContent = cssText;

                    link.parentNode.replaceChild(styleTag, link);
                    processedCount++;
                    console.log(`Оброблено ${processedCount}/${links.length}`);
                } catch (error) {
                    console.warn('Пропускаємо CSS:', link.href, error.message);
                    // Просто видаляємо посилання, якщо не вдалося завантажити
                    link.remove();
                }
            }

            console.log('CSS оброблено:', processedCount);

            // Опціонально: вбудовуємо зображення
            if (includeImages) {
                console.log('Конвертуємо зображення в base64...');
                const images = Array.from(document.querySelectorAll('img[src]'));
                let imgCount = 0;

                for (let img of images.slice(0, 20)) { // Обмежуємо 20 зображеннями
                    if (!img.src.startsWith('data:')) {
                        try {
                            const controller = new AbortController();
                            const timeoutId = setTimeout(() => controller.abort(), 5000);

                            const response = await fetch(img.src, { 
                                signal: controller.signal,
                                mode: 'cors'
                            });
                            clearTimeout(timeoutId);

                            const blob = await response.blob();
                            const base64 = await new Promise((resolve) => {
                                const reader = new FileReader();
                                reader.onloadend = () => resolve(reader.result);
                                reader.readAsDataURL(blob);
                            });
                            img.src = base64;
                            imgCount++;
                        } catch (error) {
                            console.warn('Пропускаємо зображення:', img.src);
                        }
                    }
                }
                console.log('Зображень оброблено:', imgCount);
            }

            // Повертаємо HTML
            if (selector) {
                const element = document.querySelector(selector);
                return element ? element.outerHTML : null;
            } else {
                return document.documentElement.outerHTML;
            }
        }

        return await captureHTMLWithStyles(arguments[0], arguments[1]);
        """

        print("🔄 Обробляємо стилі...")
        # Виконуємо асинхронний скрипт
        html_content = driver.execute_async_script(
            "const callback = arguments[arguments.length - 1];" +
            script +
            "captureHTMLWithStyles(arguments[0], arguments[1]).then(callback).catch(err => callback(null));",
            selector,
            include_images
        )

        if html_content:
            print("✅ HTML зібрано успішно")
        else:
            print("⚠️ Отримано порожній результат")

        return html_content

    except Exception as e:
        print(f"❌ Помилка: {e}")
        # Запасний варіант - просто збираємо HTML як є
        print("🔄 Використовуємо запасний метод...")
        try:
            html_content = driver.execute_script(
                "return document.documentElement.outerHTML;"
            )
            return html_content
        except:
            return None
    finally:
        driver.quit()


def capture_element_with_inline_styles(url, selector):
    """
    Збирає конкретний елемент з інлайн стилями (швидший метод)
    """
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-notifications')
    options.add_argument('--headless')

    driver = webdriver.Chrome(options=options)

    try:
        print("📡 Завантажуємо сторінку...")
        driver.get(url)
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, selector))
        )
        time.sleep(2)
        print("✅ Сторінка завантажена")

        # Закриваємо popup-вікна
        close_popups(driver)
        time.sleep(1)

        print("🔄 Застосовуємо інлайн стилі...")
        script = """
        function captureElementWithInlineStyles(selector) {
            const element = document.querySelector(selector);
            if (!element) return null;

            const clone = element.cloneNode(true);

            // Обробляємо сам елемент
            const origStyle = window.getComputedStyle(element);
            let styleStr = '';
            for (let prop of origStyle) {
                const value = origStyle.getPropertyValue(prop);
                if (value) styleStr += `${prop}:${value};`;
            }
            clone.setAttribute('style', styleStr);

            // Обробляємо всі дочірні елементи
            const origElements = element.querySelectorAll('*');
            const clonedElements = clone.querySelectorAll('*');

            for (let i = 0; i < origElements.length && i < 1000; i++) { // Обмежуємо 1000 елементів
                const computedStyle = window.getComputedStyle(origElements[i]);
                let elementStyle = '';
                for (let prop of computedStyle) {
                    const value = computedStyle.getPropertyValue(prop);
                    if (value) elementStyle += `${prop}:${value};`;
                }
                clonedElements[i].setAttribute('style', elementStyle);
            }

            return clone.outerHTML;
        }

        return captureElementWithInlineStyles(arguments[0]);
        """

        html_content = driver.execute_script(script, selector)
        print("✅ HTML зібрано")
        return html_content

    finally:
        driver.quit()


def close_popups(driver):
    """
    Закриває всі типові popup-вікна та overlay
    """
    print("🚫 Закриваємо popup-вікна...")

    # JavaScript для закриття popup-вікон
    popup_script = """
    // Закриваємо модальні вікна та overlay
    (function() {
        let closed = 0;

        // 1. Закриваємо за класами та атрибутами
        const selectors = [
            '[class*="modal"]',
            '[class*="popup"]',
            '[class*="overlay"]',
            '[class*="dialog"]',
            '[id*="modal"]',
            '[id*="popup"]',
            '[role="dialog"]',
            '[aria-modal="true"]',
            '.fancybox-overlay',
            '.lightbox',
            '[class*="cookie"]',
            '[class*="gdpr"]',
            '[class*="consent"]'
        ];

        selectors.forEach(selector => {
            document.querySelectorAll(selector).forEach(el => {
                // Шукаємо кнопку закриття
                const closeBtn = el.querySelector('[class*="close"], [aria-label*="close"], [aria-label*="Close"], button[class*="close"]');
                if (closeBtn) {
                    closeBtn.click();
                    closed++;
                } else {
                    // Просто ховаємо елемент
                    el.style.display = 'none';
                    el.remove();
                    closed++;
                }
            });
        });

        // 2. Видаляємо backdrop/overlay елементи
        document.querySelectorAll('[class*="backdrop"], [class*="overlay"]').forEach(el => {
            if (getComputedStyle(el).position === 'fixed') {
                el.remove();
                closed++;
            }
        });

        // 3. Видаляємо елементи з фіксованою позицією, які покривають екран
        document.querySelectorAll('div, section, aside').forEach(el => {
            const style = getComputedStyle(el);
            if (style.position === 'fixed' && 
                parseInt(style.zIndex) > 100 &&
                (el.offsetWidth > window.innerWidth * 0.5 || 
                 el.offsetHeight > window.innerHeight * 0.5)) {
                el.remove();
                closed++;
            }
        });

        // 4. Прибираємо overflow:hidden з body
        document.body.style.overflow = '';
        document.documentElement.style.overflow = '';

        return closed;
    })();
    """

    try:
        closed_count = driver.execute_script(popup_script)
        print(f"✅ Закрито елементів: {closed_count}")

        # Додатково шукаємо та клікаємо на кнопки закриття
        close_buttons = [
            "//button[contains(@class, 'close')]",
            "//button[contains(@aria-label, 'Close')]",
            "//button[contains(@aria-label, 'close')]",
            "//a[contains(@class, 'close')]",
            "//*[contains(@class, 'modal')]//button",
            "//button[text()='×']",
            "//button[text()='✕']",
            "//span[contains(@class, 'close')]"
        ]

        for xpath in close_buttons:
            try:
                buttons = driver.find_elements(By.XPATH, xpath)
                for btn in buttons[:3]:  # Закриваємо максимум 3 кнопки
                    try:
                        if btn.is_displayed():
                            btn.click()
                            print(f"  ✓ Клікнуто кнопку закриття")
                            time.sleep(0.5)
                    except:
                        pass
            except:
                pass

    except Exception as e:
        print(f"⚠️ Помилка при закритті popup: {e}")


def save_for_backend(url, selector=None, include_images=False, use_inline_styles=False):
    """
    Зберігає HTML у форматі, готовому для зберігання в БД і рендерингу
    """

    if use_inline_styles and selector:
        html_content = capture_element_with_inline_styles(url, selector)
    else:
        html_content = capture_html_for_rendering(url, selector, include_images)

    if html_content:
        return html_content
    else:
        print("\n❌ Не вдалося зібрати HTML")
        return None
