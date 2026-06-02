/* ==========================================
   NETARCHITECT MERKEZİ JAVASCRIPT DOSYASI
========================================== */

// Sayfa yüklendiğinde çalışacak fonksiyon
document.addEventListener('DOMContentLoaded', () => {
    
    // --- 1. TEMA DEĞİŞTİRİCİ (DARK/LIGHT MODE) ---
    const themeToggleBtn = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement; // <html> etiketini yakalar
    
    // Kullanıcının önceki tercihini tarayıcı hafızasından (LocalStorage) al, yoksa varsayılan olarak 'dark' yap 
    // (Çünkü projeyi genel olarak koyu temaya uyarladık)
    const currentTheme = localStorage.getItem('theme') || 'dark';
    htmlElement.setAttribute('data-bs-theme', currentTheme);
    
    if (themeToggleBtn) {
        updateButton(currentTheme);

        // Butona tıklandığında temayı değiştir
        themeToggleBtn.addEventListener('click', (e) => {
            e.preventDefault(); // Linkin sayfayı yenilemesini engelle
            const isDark = htmlElement.getAttribute('data-bs-theme') === 'dark';
            const newTheme = isDark ? 'light' : 'dark';
            
            htmlElement.setAttribute('data-bs-theme', newTheme); // Bootstrap temasını değiştir
            localStorage.setItem('theme', newTheme); // Tercihi hafızaya kaydet
            updateButton(newTheme);
        });
    }

    // Butonun görüntüsünü güncelleyen yardımcı fonksiyon
    function updateButton(theme) {
        if (!themeToggleBtn) return;
        
        if (theme === 'dark') {
            themeToggleBtn.innerHTML = '☀️ Açık Temaya Geç';
            // Eğer butonda renk sınıfları (text-light vb.) varsa burada güncelleyebilirsin
        } else {
            themeToggleBtn.innerHTML = '🌙 Koyu Temaya Geç';
        }
    }

    // --- 2. BOOTSTRAP TOOLTIP'LERİNİ TÜM SAYFALARDA OTOMATİK BAŞLAT ---
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});

// ==========================================
// ORTAK FONKSİYONLAR
// Herhangi bir HTML sayfasından çağrılabilir.
// ==========================================

// --- 3. ŞİFRE GİZLE / GÖSTER (Iconify Destekli) ---
// Örnek kullanım: onclick="togglePasswordVisibility('loginPassword', 'eyeIcon')"
function togglePasswordVisibility(inputId, iconId) {
    const passInput = document.getElementById(inputId);
    const eyeIcon = document.getElementById(iconId);
    
    if (passInput && eyeIcon) {
        if (passInput.type === 'password') {
            passInput.type = 'text';
            eyeIcon.setAttribute('data-icon', 'mdi:eye-off-outline'); // Çizgili göz ikonu
        } else {
            passInput.type = 'password';
            eyeIcon.setAttribute('data-icon', 'mdi:eye-outline'); // Normal göz ikonu
        }
    }
}

// --- 4. BUTON YÜKLENİYOR ---
// Örnek kullanım: onclick="showGlobalLoading('submitBtn', 'Kaydediliyor...')"
function showGlobalLoading(btnId, loadingText = "İşleniyor...") {
    const btn = document.getElementById(btnId);
    
    if (btn) {
        btn.innerHTML = `<span class="iconify me-2 animate-spin" data-icon="mdi:loading"></span> ${loadingText}`;
    }
}