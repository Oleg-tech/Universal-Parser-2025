import { useState, useEffect, useRef } from "react";

export default function App() {
  const [url, setUrl] = useState("");
  const [viewUrl, setViewUrl] = useState("");
  const [method, setMethod] = useState("iframe");
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedElements, setSelectedElements] = useState([]);
  const [savedFields, setSavedFields] = useState([]);
  const [showAddFieldForm, setShowAddFieldForm] = useState(false);
  const [newFieldName, setNewFieldName] = useState("");
  const contentRef = useRef(null);

  const handleKeyPress = (e) => {
    if (e.key === "Enter") {
      loadContent();
    }
  };

  const loadContent = () => {
    setError("");
    setContent("");
    setLoading(true);
    
    let processedUrl = url.trim();
    if (processedUrl && !processedUrl.startsWith('http://') && !processedUrl.startsWith('https://')) {
      processedUrl = 'https://' + processedUrl;
    }
    
    setViewUrl(processedUrl);
    setMethod("iframe");
    setLoading(false);
  };

  const switchToFetchMethod = async () => {
    console.log("Переключаюся на fetch метод...");
    setMethod("fetch");
    setLoading(true);
    setError("");
    
    try {
      // Спробуємо завантажити через fetch з різними CORS proxy
      const proxies = [
        `https://api.allorigins.win/get?url=${encodeURIComponent(viewUrl)}`,
        `https://corsproxy.io/?${encodeURIComponent(viewUrl)}`,
        `https://api.codetabs.com/v1/proxy?quest=${encodeURIComponent(viewUrl)}`
      ];

      let success = false;
      for (const proxy of proxies) {
        try {
          console.log(`Спробую proxy: ${proxy}`);
          const response = await fetch(proxy);
          if (response.ok) {
            let html;
            const contentType = response.headers.get('content-type');
            
            if (proxy.includes('allorigins.win')) {
              const data = await response.json();
              html = data.contents;
            } else {
              html = await response.text();
            }
            
            // Модифікуємо HTML для коректного відображення
            html = modifyHtml(html, viewUrl);
            setContent(html);
            success = true;
            console.log("Успішно завантажено через proxy!");
            break;
          }
        } catch (proxyError) {
          console.log(`Proxy ${proxy} не спрацював:`, proxyError);
        }
      }
      
      if (!success) {
        throw new Error("Всі методи завантаження не спрацювали. Сайт має дуже строгі обмеження безпеки.");
      }
    } catch (fetchError) {
      setError(`Не вдалося завантажити сайт: ${fetchError.message}`);
    }
    
    setLoading(false);
  };

  // Використовуємо useEffect для додавання listeners після рендерингу HTML
  useEffect(() => {
    if (method === "fetch" && content && selectionMode && contentRef.current) {
      // Невеликий timeout щоб переконатися, що DOM оновився
      const timer = setTimeout(() => {
        addSelectionListeners();
      }, 100);
      
      return () => {
        clearTimeout(timer);
        removeSelectionListeners();
      };
    }
  }, [content, selectionMode, method]);

  const checkIframeContent = (iframe) => {
    // Перевіряємо через певний час, чи завантажився iframe
    const checkTimeout = setTimeout(() => {
      try {
        // Перевіряємо чи можемо отримати доступ до вмісту iframe
        const iframeDoc = iframe.contentDocument || iframe.contentWindow?.document;
        
        if (!iframeDoc) {
          console.log("Немає доступу до документу iframe - переключаюся на fetch");
          switchToFetchMethod();
          return;
        }

        // Перевіряємо чи є текст з помилкою в iframe
        const iframeBody = iframeDoc.body;
        if (iframeBody) {
          const bodyText = iframeBody.textContent || iframeBody.innerText || '';
          
          // Шукаємо типові повідомлення про відхилення з'єднання
          const connectionRefusedMessages = [
            'відхилив запит на з\'єднання',
            'refused to connect',
            'connection was refused',
            'відмовив у з\'єднанні',
            'ERR_CONNECTION_REFUSED',
            'This site can\'t be reached',
            'Цей сайт недоступний'
          ];
          
          const hasConnectionError = connectionRefusedMessages.some(msg => 
            bodyText.toLowerCase().includes(msg.toLowerCase())
          );
          
          if (hasConnectionError) {
            console.log("Знайдено повідомлення про відхилення з'єднання - переключаюся на fetch");
            switchToFetchMethod();
            return;
          }
        }
        
        // Додаткова перевірка - чи iframe порожній або має помилку
        if (!iframeDoc.body || iframeDoc.body.children.length === 0) {
          const html = iframeDoc.documentElement?.innerHTML || '';
          if (html.length < 100) { // Якщо HTML дуже короткий, можливо це помилка
            console.log("iframe порожній або має помилку - переключаюся на fetch");
            switchToFetchMethod();
          }
        }
        
      } catch (error) {
        // Якщо не можемо отримати доступ до iframe через CORS
        console.log("CORS блокування iframe - переключаюся на fetch");
        switchToFetchMethod();
      }
    }, 4000); // Чекаємо 4 секунди на завантаження

    return checkTimeout;
  };

  const modifyHtml = (html, baseUrl) => {
    try {
      const baseUrlObj = new URL(baseUrl);
      const baseHref = `${baseUrlObj.protocol}//${baseUrlObj.host}`;
      
      // Додаємо base tag для коректного завантаження ресурсів
      html = html.replace(/<head>/i, `<head><base href="${baseHref}">`);
      
      // Замінюємо відносні посилання на абсолютні
      html = html.replace(/src="\/([^"]*)"/g, `src="${baseHref}/$1"`);
      html = html.replace(/href="\/([^"]*)"/g, `href="${baseHref}/$1"`);
      html = html.replace(/url\(\/([^)]*)\)/g, `url(${baseHref}/$1)`);
      
      // Видаляємо небезпечні скрипти та мета-теги, які можуть перенаправляти
      html = html.replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '');
      html = html.replace(/<meta[^>]*http-equiv[^>]*>/gi, '');
      
      // Додаємо CSS стилі для виділення елементів
      const selectionCSS = `
        <style id="element-selection-styles">
          .element-hover {
            outline: 2px dashed #007bff !important;
            outline-offset: 2px !important;
            cursor: pointer !important;
            position: relative !important;
            z-index: 9999 !important;
          }
          .element-selected {
            outline: 3px solid #007bff !important;
            outline-offset: 2px !important;
            background-color: rgba(0, 123, 255, 0.1) !important;
            position: relative !important;
            z-index: 9999 !important;
          }
          .element-selected::before {
            content: '✓ Вибрано';
            position: absolute !important;
            top: -25px !important;
            left: 0 !important;
            background: #007bff !important;
            color: white !important;
            padding: 2px 6px !important;
            font-size: 12px !important;
            border-radius: 3px !important;
            z-index: 10000 !important;
            font-family: Arial, sans-serif !important;
            pointer-events: none !important;
          }
        </style>
      `;
      
      // Вставляємо CSS в head
      html = html.replace(/<\/head>/i, `${selectionCSS}</head>`);
      
      return html;
    } catch (e) {
      console.log("Помилка при модифікації HTML:", e);
      return html;
    }
  };

  const enableSelectionMode = () => {
    setSelectionMode(true);
    setSelectedElements([]);
  };

  const disableSelectionMode = () => {
    setSelectionMode(false);
    removeSelectionListeners();
    // Очищаємо виділення
    if (contentRef.current) {
      const selectedElements = contentRef.current.querySelectorAll('.element-selected, .element-hover');
      selectedElements.forEach(el => {
        el.classList.remove('element-selected', 'element-hover');
      });
    }
    setSelectedElements([]);
  };

  const addSelectionListeners = () => {
    const contentDiv = contentRef.current;
    if (!contentDiv) {
      console.log("contentRef.current не знайдено");
      return;
    }

    console.log("Додаю selection listeners до:", contentDiv);

    const handleMouseOver = (e) => {
      if (!selectionMode) return;
      e.stopPropagation();
      
      // Ігноруємо сам контейнер
      if (e.target === contentDiv) return;
      
      // Видаляємо попередній hover
      const prevHover = contentDiv.querySelector('.element-hover');
      if (prevHover) prevHover.classList.remove('element-hover');
      
      // Додаємо hover до поточного елемента
      e.target.classList.add('element-hover');

      // Лог: показуємо на який елемент наведено
      console.log("Наведено на елемент:", {
        tagName: e.target.tagName.toLowerCase(),
        id: e.target.id || "без id",
        className: e.target.className || "без class",
        text: (e.target.textContent || "").trim().substring(0, 50) +
              ((e.target.textContent || "").length > 50 ? "..." : "")
      });
    };

    const handleMouseOut = (e) => {
      if (!selectionMode) return;
      e.stopPropagation();
      
      // Ігноруємо сам контейнер
      if (e.target === contentDiv) return;
      
      e.target.classList.remove('element-hover');
    };

    const handleClick = (e) => {
      if (!selectionMode) return;
      e.preventDefault();
      e.stopPropagation();
      
      const element = e.target;
      
      // Ігноруємо сам контейнер
      if (element === contentDiv) return;
      
      console.log("Клік по елементу:", element.tagName);
      
      // Переключаємо стан виділення
      if (element.classList.contains('element-selected')) {
        element.classList.remove('element-selected');
        setSelectedElements(prev => prev.filter(el => el !== element));
      } else {
        element.classList.add('element-selected');
        element.classList.remove('element-hover');
        setSelectedElements(prev => [...prev, element]);
      }
    };

    // Використовуємо event delegation - додаємо один listener до контейнера
    contentDiv.addEventListener('mouseover', handleMouseOver, true);
    contentDiv.addEventListener('mouseout', handleMouseOut, true);
    contentDiv.addEventListener('click', handleClick, true);
    
    // Зберігаємо посилання на слухачі для їх видалення пізніше
    contentDiv._selectionListeners = { handleMouseOver, handleMouseOut, handleClick };
    
    console.log("Selection listeners додано успішно");
  };

  const removeSelectionListeners = () => {
    const contentDiv = contentRef.current;
    if (!contentDiv || !contentDiv._selectionListeners) return;

    const { handleMouseOver, handleMouseOut, handleClick } = contentDiv._selectionListeners;
    
    contentDiv.removeEventListener('mouseover', handleMouseOver, true);
    contentDiv.removeEventListener('mouseout', handleMouseOut, true);
    contentDiv.removeEventListener('click', handleClick, true);
    
    delete contentDiv._selectionListeners;
    console.log("Selection listeners видалено");
  };

  const getSelectedElementsInfo = () => {
    return selectedElements.map((el, index) => ({
      index: index + 1,
      tagName: el.tagName.toLowerCase(),
      id: el.id || 'без id',
      className: el.className || 'без class',
      text: (el.textContent || '').substring(0, 50) + (el.textContent?.length > 50 ? '...' : ''),
      innerHTML: el.innerHTML.substring(0, 100) + (el.innerHTML?.length > 100 ? '...' : '')
    }));
  };

  // Функція для отримання всіх атрибутів елемента
  const getElementAttributes = (element) => {
    const attributes = {};
    for (let i = 0; i < element.attributes.length; i++) {
      const attr = element.attributes[i];
      attributes[attr.name] = attr.value;
    }
    return attributes;
  };

  // Функція для додавання нового поля
  const addNewField = () => {
    if (!newFieldName.trim()) {
      alert("Введіть назву поля!");
      return;
    }

    if (selectedElements.length === 0) {
      alert("Виберіть хоча б один елемент!");
      return;
    }

    const newField = {
      id: Date.now(), // Унікальний ID
      name: newFieldName.trim(),
      elements: selectedElements.map(element => ({
        tagName: element.tagName.toLowerCase(),
        attributes: getElementAttributes(element),
        textContent: element.textContent?.trim() || '',
        innerHTML: element.innerHTML,
        outerHTML: element.outerHTML
      })),
      createdAt: new Date().toLocaleString('uk-UA')
    };

    setSavedFields(prev => [...prev, newField]);
    setNewFieldName("");
    setShowAddFieldForm(false);
    
    // Очищуємо вибрані елементи
    disableSelectionMode();
    
    alert(`Поле "${newFieldName}" збережено з ${selectedElements.length} елементами!`);
  };

  // Функція для видалення поля
  const deleteField = (fieldId) => {
    if (confirm("Ви впевнені, що хочете видалити це поле?")) {
      setSavedFields(prev => prev.filter(field => field.id !== fieldId));
    }
  };

  return (
    <div style={{ padding: "20px", fontFamily: "sans-serif" }}>
      <h1>Відкрити сторінку за посиланням</h1>
      
      <div style={{ marginBottom: "20px" }}>
        <input
          type="text"
          placeholder="Встав посилання і натисни Enter"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={handleKeyPress}
          style={{
            width: "400px",
            padding: "8px",
            fontSize: "16px",
            borderRadius: "8px",
            border: "1px solid gray",
            marginRight: "10px"
          }}
        />
        <button 
          onClick={loadContent}
          disabled={loading}
          style={{
            padding: "8px 16px",
            fontSize: "16px",
            borderRadius: "8px",
            border: "1px solid #007bff",
            backgroundColor: loading ? "#ccc" : "#007bff",
            color: "white",
            cursor: loading ? "not-allowed" : "pointer",
            marginRight: "10px"
          }}
        >
          {loading ? "Завантаження..." : "Завантажити"}
        </button>

        {/* Кнопки для режиму виділення */}
        {viewUrl && method === "fetch" && content && (
          <>
            {!selectionMode ? (
              <button 
                onClick={enableSelectionMode}
                style={{
                  padding: "8px 16px",
                  fontSize: "16px",
                  borderRadius: "8px",
                  border: "1px solid #28a745",
                  backgroundColor: "#28a745",
                  color: "white",
                  cursor: "pointer",
                  marginRight: "10px"
                }}
              >
                🎯 Режим виділення
              </button>
            ) : (
              <button 
                onClick={disableSelectionMode}
                style={{
                  padding: "8px 16px",
                  fontSize: "16px",
                  borderRadius: "8px",
                  border: "1px solid #dc3545",
                  backgroundColor: "#dc3545",
                  color: "white",
                  cursor: "pointer",
                  marginRight: "10px"
                }}
              >
                ❌ Вимкнути виділення
              </button>
            )}

            {/* Кнопка "Додати поле" */}
            {selectedElements.length > 0 && (
              <button 
                onClick={() => setShowAddFieldForm(true)}
                style={{
                  padding: "8px 16px",
                  fontSize: "16px",
                  borderRadius: "8px",
                  border: "1px solid #fd7e14",
                  backgroundColor: "#fd7e14",
                  color: "white",
                  cursor: "pointer",
                  marginRight: "10px"
                }}
              >
                ➕ Додати поле
              </button>
            )}
          </>
        )}
      </div>

      {/* Форма додавання поля */}
      {showAddFieldForm && (
        <div style={{
          marginBottom: "20px",
          padding: "15px",
          backgroundColor: "#fff3cd",
          borderRadius: "8px",
          border: "1px solid #ffeaa7"
        }}>
          <h4 style={{ margin: "0 0 10px 0" }}>Додати нове поле</h4>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <input
              type="text"
              placeholder="Назва поля (наприклад: заголовки, ціни, описи)"
              value={newFieldName}
              onChange={(e) => setNewFieldName(e.target.value)}
              style={{
                flex: 1,
                padding: "8px",
                fontSize: "14px",
                borderRadius: "4px",
                border: "1px solid #ddd"
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  addNewField();
                }
              }}
            />
            <button 
              onClick={addNewField}
              style={{
                padding: "8px 16px",
                fontSize: "14px",
                borderRadius: "4px",
                border: "1px solid #28a745",
                backgroundColor: "#28a745",
                color: "white",
                cursor: "pointer"
              }}
            >
              💾 Зберегти поле
            </button>
            <button 
              onClick={() => setShowAddFieldForm(false)}
              style={{
                padding: "8px 16px",
                fontSize: "14px",
                borderRadius: "4px",
                border: "1px solid #6c757d",
                backgroundColor: "#6c757d",
                color: "white",
                cursor: "pointer"
              }}
            >
              Скасувати
            </button>
          </div>
          <div style={{ marginTop: "8px", fontSize: "12px", color: "#856404" }}>
            Вибрано елементів: {selectedElements.length}. Всі вибрані елементи будуть збережені в цьому полі.
          </div>
        </div>
      )}

      {/* Відображення збережених полів */}
      {savedFields.length > 0 && (
        <div style={{
          marginBottom: "20px",
          padding: "15px",
          backgroundColor: "#d1ecf1",
          borderRadius: "8px",
          border: "1px solid #b6d7ff"
        }}>
          <h3 style={{ margin: "0 0 15px 0" }}>📋 Збережені поля ({savedFields.length})</h3>
          {savedFields.map((field) => (
            <div key={field.id} style={{
              marginBottom: "15px",
              padding: "12px",
              backgroundColor: "white",
              borderRadius: "6px",
              border: "1px solid #e9ecef"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                <h4 style={{ margin: 0, color: "#0c5460" }}>{field.name}</h4>
                <div style={{ display: "flex", gap: "5px" }}>
                  <span style={{ fontSize: "12px", color: "#6c757d" }}>{field.createdAt}</span>
                  <button
                    onClick={() => deleteField(field.id)}
                    style={{
                      padding: "2px 6px",
                      fontSize: "12px",
                      borderRadius: "3px",
                      border: "1px solid #dc3545",
                      backgroundColor: "#dc3545",
                      color: "white",
                      cursor: "pointer"
                    }}
                  >
                    🗑️
                  </button>
                </div>
              </div>
              <div style={{ fontSize: "13px", color: "#495057" }}>
                <strong>Елементів:</strong> {field.elements.length}
              </div>
              
              {/* Детальна інформація про елементи */}
              <div style={{ marginTop: "10px", maxHeight: "200px", overflow: "auto" }}>
                {field.elements.map((element, elemIndex) => (
                  <div key={elemIndex} style={{
                    marginBottom: "8px",
                    padding: "8px",
                    backgroundColor: "#f8f9fa",
                    borderRadius: "4px",
                    border: "1px solid #e9ecef",
                    fontSize: "12px"
                  }}>
                    <div style={{ marginBottom: "4px" }}>
                      <strong>#{elemIndex + 1} &lt;{element.tagName}&gt;</strong>
                    </div>
                    
                    {/* Атрибути */}
                    {Object.keys(element.attributes).length > 0 && (
                      <div style={{ marginBottom: "4px" }}>
                        <strong>Атрибути:</strong>
                        {Object.entries(element.attributes).map(([name, value]) => (
                          <span key={name} style={{ 
                            marginLeft: "8px", 
                            padding: "1px 4px", 
                            backgroundColor: "#e9ecef", 
                            borderRadius: "2px",
                            fontSize: "11px"
                          }}>
                            {name}="{value}"
                          </span>
                        ))}
                      </div>
                    )}
                    
                    {/* Текст */}
                    {element.textContent && (
                      <div style={{ color: "#6c757d" }}>
                        <strong>Текст:</strong> {element.textContent.substring(0, 100)}
                        {element.textContent.length > 100 ? "..." : ""}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Інформація про режим виділення */}
      {viewUrl && method === "fetch" && content && selectionMode && (
        <div style={{ 
          marginBottom: "15px", 
          padding: "10px", 
          backgroundColor: "#e3f2fd",
          borderRadius: "6px",
          border: "1px solid #90caf9"
        }}>
          <div style={{ fontWeight: "bold", marginBottom: "5px" }}>🎯 Режим виділення активний</div>
          <div style={{ fontSize: "14px", color: "#1565c0" }}>
            • Наведіть мишку на елемент, щоб побачити підсвітку<br/>
            • Клікніть на елемент, щоб виділити його<br/>
            • Вибрано елементів: {selectedElements.length}
          </div>
        </div>
      )}
      
      {viewUrl && (
        <div style={{ 
          marginBottom: "15px", 
          padding: "8px 12px", 
          backgroundColor: method === "iframe" ? "#d4edda" : "#fff3cd",
          borderRadius: "6px",
          border: `1px solid ${method === "iframe" ? "#c3e6cb" : "#ffeaa7"}`,
          fontSize: "14px"
        }}>
          <strong>Поточний метод:</strong> {method === "iframe" ? "iframe (швидко)" : "fetch + innerHTML (резервний метод)"}
          {method === "fetch" && " - JavaScript відключений, але контент відображається"}
        </div>
      )}

      {/* Відображення помилок */}
      {error && (
        <div style={{
          backgroundColor: "#f8d7da",
          color: "#721c24",
          padding: "12px",
          borderRadius: "8px",
          marginBottom: "20px",
          border: "1px solid #f5c6cb"
        }}>
          <strong>Помилка:</strong> {error}
        </div>
      )}

      {/* Контент */}
      {viewUrl && (
        <div style={{ marginTop: "20px" }}>
          {method === "iframe" && (
            <iframe
              src={viewUrl}
              title="Website Preview"
              style={{
                width: "100%",
                height: "80vh",
                border: "1px solid black",
                borderRadius: "8px"
              }}
              onError={() => {
                console.log("iframe onError спрацював");
                switchToFetchMethod();
              }}
              onLoad={(e) => {
                const iframe = e.target;
                console.log("iframe завантажився, перевіряю вміст...");
                
                // Запускаємо перевірку вмісту iframe
                checkIframeContent(iframe);
              }}
            />
          )}
          
          {method === "fetch" && loading && (
            <div style={{
              width: "100%",
              height: "80vh",
              border: "1px solid black",
              borderRadius: "8px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              backgroundColor: "#f8f9fa",
              flexDirection: "column"
            }}>
              <div style={{ fontSize: "18px", marginBottom: "10px" }}>Завантаження через резервний метод...</div>
              <div style={{ fontSize: "14px", color: "#666" }}>iframe заблокований, використовуємо fetch + innerHTML</div>
            </div>
          )}
          
          {method === "fetch" && content && !loading && (
            <>
              <div
                ref={contentRef}
                style={{
                  width: "100%",
                  height: "80vh",
                  border: "1px solid black",
                  borderRadius: "8px",
                  overflow: "auto",
                  backgroundColor: "white"
                }}
                dangerouslySetInnerHTML={{ __html: content }}
              />
              
              {/* Інформація про вибрані елементи */}
              {selectedElements.length > 0 && (
                <div style={{
                  marginTop: "15px",
                  padding: "15px",
                  backgroundColor: "#e7f3ff",
                  borderRadius: "8px",
                  border: "1px solid #b3d9ff"
                }}>
                  <h4 style={{ margin: "0 0 10px 0" }}>Вибрані елементи ({selectedElements.length}):</h4>
                  <div style={{ maxHeight: "200px", overflow: "auto" }}>
                    {getSelectedElementsInfo().map((info, index) => (
                      <div key={index} style={{
                        padding: "8px",
                        marginBottom: "8px",
                        backgroundColor: "white",
                        borderRadius: "4px",
                        border: "1px solid #e9ecef",
                        fontSize: "13px"
                      }}>
                        <strong>#{info.index} {info.tagName}</strong>
                        {info.id !== 'без id' && <span style={{ color: "#007bff" }}> id="{info.id}"</span>}
                        {info.className !== 'без class' && <span style={{ color: "#28a745" }}> class="{info.className}"</span>}
                        <div style={{ marginTop: "4px", color: "#666" }}>
                          Текст: {info.text || 'порожній'}
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  <button 
                    onClick={() => setSelectedElements([])}
                    style={{
                      marginTop: "10px",
                      padding: "6px 12px",
                      fontSize: "14px",
                      borderRadius: "4px",
                      border: "1px solid #6c757d",
                      backgroundColor: "#6c757d",
                      color: "white",
                      cursor: "pointer",
                      marginRight: "10px"
                    }}
                  >
                    Очистити вибір
                  </button>
                  
                  <button 
                    onClick={() => setShowAddFieldForm(true)}
                    style={{
                      padding: "6px 12px",
                      fontSize: "14px",
                      borderRadius: "4px",
                      border: "1px solid #fd7e14",
                      backgroundColor: "#fd7e14",
                      color: "white",
                      cursor: "pointer"
                    }}
                  >
                    ➕ Додати поле
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}
      
      {/* Інформація */}
      <div style={{
        marginTop: "20px",
        padding: "15px",
        backgroundColor: "#e9ecef",
        borderRadius: "8px",
        fontSize: "14px"
      }}>
        <h4>Як це працює:</h4>
        <ol>
          <li>Спочатку намагаємося завантажити через <strong>iframe</strong> (найшвидший метод)</li>
          <li>Якщо iframe блокується сайтом, автоматично переключаємося на <strong>fetch + innerHTML</strong></li>
          <li>Fetch метод завантажує HTML код через CORS proxy і відображає його безпосередньо</li>
          <li>JavaScript сайту відключається з міркувань безпеки, але контент відображається</li>
          <li><strong>Нова функція:</strong> Виділяйте елементи та зберігайте їх як поля з повною інформацією про теги та атрибути</li>
        </ol>
        
        <h4 style={{ marginTop: "15px" }}>Робота з полями:</h4>
        <ul>
          <li>Увімкніть режим виділення та натисніть на потрібні елементи</li>
          <li>Натисніть "Додати поле" та вкажіть назву (наприклад: "заголовки", "ціни", "описи")</li>
          <li>Всі вибрані елементи збережуться з повною інформацією про теги, атрибути та контент</li>
          <li>Збережені поля відображаються вгорі сторінки з детальною інформацією</li>
        </ul>
      </div>
    </div>
  );
}