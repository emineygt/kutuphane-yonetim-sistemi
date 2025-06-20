from flask import Flask, render_template, request, jsonify
import oracledb
from dotenv import load_dotenv
import os


load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'gizli-anahtar-123')

# Oracle veritabanı bağlantı bilgileri
oracle_connection = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'dsn': f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
}

def get_db_connection():
    try:
        connection = oracledb.connect(**oracle_connection)
        # Schema'yı library1 olarak ayarla
        with connection.cursor() as cursor:
            cursor.execute("ALTER SESSION SET CURRENT_SCHEMA = library1")
        return connection
    except Exception as e:
        print(f"Veritabanı bağlantı hatası: {str(e)}")
        raise e

@app.route('/')
def index():
    return render_template('index.html')

# Kütüphane işlemleri
@app.route('/kutuphane/getir')
def kutuphane_getir():
    ulke = request.args.get('ulke', '')
    sehir = request.args.get('sehir', '')
    
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                base_query = """
                    SELECT l.library_id, l.name, l.opening_hours, loc.country, loc.city
                    FROM Libraries l
                    JOIN Location loc ON l.location_id = loc.location_id
                """
                where_clause = []
                params = {}
                
                if ulke:
                    where_clause.append("LOWER(loc.country) LIKE LOWER(:ulke)")
                    params['ulke'] = f"%{ulke}%"
                if sehir:
                    where_clause.append("LOWER(loc.city) LIKE LOWER(:sehir)")
                    params['sehir'] = f"%{sehir}%"
                
                if where_clause:
                    base_query += " WHERE " + " AND ".join(where_clause)
                
                cursor.execute(base_query, params)
                kutuphaneler = cursor.fetchall()
                
                return jsonify({'kutuphaneler': [
                    {
                        'id': k[0],
                        'ad': k[1],
                        'calisma_saatleri': k[2],
                        'ulke': k[3],
                        'sehir': k[4]
                    } for k in kutuphaneler
                ]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/kutuphane/ekle', methods=['POST'])
def kutuphane_ekle():
    data = request.json
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                # Önce location ekle
                location_id = cursor.var(int)
                cursor.execute("""
                    INSERT INTO Location (location_id, country, city)
                    VALUES (
                        (SELECT NVL(MAX(location_id), 0) + 1 FROM Location),
                        :ulke,
                        :sehir
                    )
                    RETURNING location_id INTO :location_id
                """, {
                    'ulke': data['ulke'],
                    'sehir': data['sehir'],
                    'location_id': location_id
                })
                
                # Sonra kütüphane ekle
                cursor.execute("""
                    INSERT INTO Libraries (library_id, name, opening_hours, location_id)
                    VALUES (
                        (SELECT NVL(MAX(library_id), 0) + 1 FROM Libraries),
                        :ad,
                        :calisma_saatleri,
                        :location_id
                    )
                """, {
                    'ad': data['ad'],
                    'calisma_saatleri': data.get('calisma_saatleri'),
                    'location_id': location_id.getvalue()[0]
                })
                
                connection.commit()
                return jsonify({'message': 'Kütüphane başarıyla eklendi'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Çalışan işlemleri
@app.route('/calisan/getir')
def calisan_getir():
    ulke = request.args.get('ulke', '')
    sehir = request.args.get('sehir', '')
    kutuphane = request.args.get('kutuphane', '')
    
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                base_query = """
                    SELECT ls.staff_id, ls.name, ls.job_title, ls.contact_number,
                           l.name as library_name, loc.country, loc.city
                    FROM Library_Staff ls
                    JOIN Libraries l ON ls.library_id = l.library_id
                    JOIN Location loc ON l.location_id = loc.location_id
                """
                where_clause = []
                params = {}
                
                if ulke:
                    where_clause.append("LOWER(loc.country) LIKE LOWER(:ulke)")
                    params['ulke'] = f"%{ulke}%"
                if sehir:
                    where_clause.append("LOWER(loc.city) LIKE LOWER(:sehir)")
                    params['sehir'] = f"%{sehir}%"
                if kutuphane:
                    where_clause.append("LOWER(l.name) LIKE LOWER(:kutuphane)")
                    params['kutuphane'] = f"%{kutuphane}%"
                
                if where_clause:
                    base_query += " WHERE " + " AND ".join(where_clause)
                
                cursor.execute(base_query, params)
                calisanlar = cursor.fetchall()
                
                return jsonify({'calisanlar': [
                    {
                        'id': c[0],
                        'ad': c[1],
                        'pozisyon': c[2],
                        'telefon': c[3],
                        'kutuphane': c[4],
                        'ulke': c[5],
                        'sehir': c[6]
                    } for c in calisanlar
                ]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/calisan/ekle', methods=['POST'])
def calisan_ekle():
    data = request.json
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO Library_Staff (staff_id, name, job_title, contact_number, library_id)
                    VALUES (
                        (SELECT NVL(MAX(staff_id), 0) + 1 FROM Library_Staff),
                        :ad,
                        :pozisyon,
                        :telefon,
                        :kutuphane_id
                    )
                """, {
                    'ad': data['ad'],
                    'pozisyon': data['pozisyon'],
                    'telefon': data['telefon'],
                    'kutuphane_id': data['kutuphane_id']
                })
                
                connection.commit()
                return jsonify({'message': 'Çalışan başarıyla eklendi'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/sponsor/getir')
def sponsor_getir():
    ulke = request.args.get('ulke', '')
    sehir = request.args.get('sehir', '')
    kutuphane = request.args.get('kutuphane', '')
    
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                base_query = """
                    SELECT f.funder_id, f.name, l.name as library_name, 
                           loc.country, loc.city
                    FROM Funders f
                    JOIN Library_Funders lf ON f.funder_id = lf.funder_id
                    JOIN Libraries l ON lf.library_id = l.library_id
                    JOIN Location loc ON l.location_id = loc.location_id
                """
                where_clause = []
                params = {}
                
                if ulke:
                    where_clause.append("LOWER(loc.country) LIKE LOWER(:ulke)")
                    params['ulke'] = f"%{ulke}%"
                if sehir:
                    where_clause.append("LOWER(loc.city) LIKE LOWER(:sehir)")
                    params['sehir'] = f"%{sehir}%"
                if kutuphane:
                    where_clause.append("LOWER(l.name) LIKE LOWER(:kutuphane)")
                    params['kutuphane'] = f"%{kutuphane}%"
                
                if where_clause:
                    base_query += " WHERE " + " AND ".join(where_clause)
                
                cursor.execute(base_query, params)
                sponsorlar = cursor.fetchall()
                
                return jsonify({'sponsorlar': [
                    {
                        'id': s[0],
                        'ad': s[1],
                        'kutuphane': s[2],
                        'ulke': s[3],
                        'sehir': s[4]
                    } for s in sponsorlar
                ]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/sponsor/ekle', methods=['POST'])
def sponsor_ekle():
    data = request.json
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                # Önce sponsor ekle
                funder_id = cursor.var(int)
                cursor.execute("""
                    INSERT INTO Funders (funder_id, name)
                    VALUES (
                        (SELECT NVL(MAX(funder_id), 0) + 1 FROM Funders),
                        :ad
                    )
                    RETURNING funder_id INTO :funder_id
                """, {
                    'ad': data['ad'],
                    'funder_id': funder_id
                })
                
                # Sonra kütüphane-sponsor ilişkisini ekle
                cursor.execute("""
                    INSERT INTO Library_Funders (library_id, funder_id)
                    VALUES (:kutuphane_id, :funder_id)
                """, {
                    'kutuphane_id': data['kutuphane_id'],
                    'funder_id': funder_id.getvalue()[0]
                })
                
                connection.commit()
                return jsonify({'message': 'Sponsor başarıyla eklendi'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ziyaretci/getir')
def ziyaretci_getir():
    ulke = request.args.get('ulke', '')
    sehir = request.args.get('sehir', '')
    kutuphane = request.args.get('kutuphane', '')
    
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                base_query = """
                    SELECT DISTINCT v.visitor_id, v.name, v.surname, v.email, v.phone_number,
                           l.name as library_name, loc.country, loc.city
                    FROM Visitors v
                    JOIN Visitor_Library vl ON v.visitor_id = vl.visitor_id
                    JOIN Libraries l ON vl.library_id = l.library_id
                    JOIN Location loc ON l.location_id = loc.location_id
                """
                where_clause = []
                params = {}
                
                if ulke:
                    where_clause.append("LOWER(loc.country) LIKE LOWER(:ulke)")
                    params['ulke'] = f"%{ulke}%"
                if sehir:
                    where_clause.append("LOWER(loc.city) LIKE LOWER(:sehir)")
                    params['sehir'] = f"%{sehir}%"
                if kutuphane:
                    where_clause.append("LOWER(l.name) LIKE LOWER(:kutuphane)")
                    params['kutuphane'] = f"%{kutuphane}%"
                
                if where_clause:
                    base_query += " WHERE " + " AND ".join(where_clause)
                
                cursor.execute(base_query, params)
                ziyaretciler = cursor.fetchall()
                
                return jsonify({'ziyaretciler': [
                    {
                        'id': z[0],
                        'ad': z[1],
                        'soyad': z[2],
                        'email': z[3],
                        'telefon': z[4],
                        'kutuphane': z[5],
                        'ulke': z[6],
                        'sehir': z[7]
                    } for z in ziyaretciler
                ]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ziyaretci/ekle', methods=['POST'])
def ziyaretci_ekle():
    data = request.json
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                # Önce ziyaretçi ekle
                visitor_id = cursor.var(int)
                cursor.execute("""
                    INSERT INTO Visitors (visitor_id, name, surname, email, phone_number)
                    VALUES (
                        (SELECT NVL(MAX(visitor_id), 0) + 1 FROM Visitors),
                        :ad,
                        :soyad,
                        :email,
                        :telefon
                    )
                    RETURNING visitor_id INTO :visitor_id
                """, {
                    'ad': data['ad'],
                    'soyad': data['soyad'],
                    'email': data.get('email'),
                    'telefon': data.get('telefon'),
                    'visitor_id': visitor_id
                })
                
                # Sonra ziyaretçi-kütüphane ilişkisini ekle
                cursor.execute("""
                    INSERT INTO Visitor_Library (visitor_id, library_id)
                    VALUES (:visitor_id, :kutuphane_id)
                """, {
                    'visitor_id': visitor_id.getvalue()[0],
                    'kutuphane_id': data['kutuphane_id']
                })
                
                connection.commit()
                return jsonify({'message': 'Ziyaretçi başarıyla eklendi'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ziyaretci/sil/<int:visitor_id>', methods=['DELETE'])
def ziyaretci_sil(visitor_id):
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                # Önce ziyaretçi ile ilgili tüm ilişkileri sil
                cursor.execute("""
                    DELETE FROM Visitor_Library
                    WHERE visitor_id = :visitor_id
                """, {'visitor_id': visitor_id})
                
                # Diğer olası ilişkileri de sil
                cursor.execute("""
                    DELETE FROM Loans
                    WHERE visitor_id = :visitor_id
                """, {'visitor_id': visitor_id})
                
                # Son olarak ziyaretçiyi sil
                cursor.execute("""
                    DELETE FROM Visitors
                    WHERE visitor_id = :visitor_id
                """, {'visitor_id': visitor_id})
                
                connection.commit()
                return jsonify({'message': 'Ziyaretçi başarıyla silindi'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ziyaretci/duzenle/<int:visitor_id>', methods=['PUT'])
def ziyaretci_duzenle(visitor_id):
    data = request.json
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                # Ziyaretçi bilgilerini güncelle
                cursor.execute("""
                    UPDATE Visitors
                    SET name = :ad,
                        surname = :soyad,
                        email = :email,
                        phone_number = :telefon
                    WHERE visitor_id = :visitor_id
                """, {
                    'ad': data['ad'],
                    'soyad': data['soyad'],
                    'email': data.get('email'),
                    'telefon': data.get('telefon'),
                    'visitor_id': visitor_id
                })
                
                # Eğer kütüphane değişikliği varsa, ilişkiyi güncelle
                if 'kutuphane_id' in data:
                    cursor.execute("""
                        UPDATE Visitor_Library
                        SET library_id = :kutuphane_id
                        WHERE visitor_id = :visitor_id
                    """, {
                        'kutuphane_id': data['kutuphane_id'],
                        'visitor_id': visitor_id
                    })
                
                connection.commit()
                return jsonify({'message': 'Ziyaretçi başarıyla güncellendi'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# İstatistik sorguları
@app.route('/istatistik/aylik-kiralama')
def aylik_kiralama_istatistik():
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        TO_CHAR(l.loan_date, 'YYYY-MM') AS month,
                        COUNT(*) AS loan_count
                    FROM 
                        Loans l
                    JOIN 
                        Library_Books lb ON l.library_book_id = lb.library_book_id
                    JOIN 
                        Libraries lib ON lb.library_id = lib.library_id
                    JOIN 
                        Location loc ON lib.location_id = loc.location_id
                    WHERE 
                        loc.country = 'Türkiye'
                    GROUP BY 
                        TO_CHAR(l.loan_date, 'YYYY-MM')
                    ORDER BY 
                        month
                """)
                
                sonuclar = cursor.fetchall()
                return jsonify({'aylik_kiralama': [
                    {
                        'ay': sonuc[0],
                        'kiralama_sayisi': sonuc[1]
                    } for sonuc in sonuclar
                ]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/istatistik/kitap-durumu')
def kitap_durumu_istatistik():
    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        b.title AS kitap_adi,
                        COUNT(l.loan_id) AS kiralanma_sayisi,
                        SUM(lb.quantity) - COUNT(l.loan_id) AS kiralanabilir_adet
                    FROM 
                        Library_Books lb
                    JOIN 
                        Books b ON lb.book_id = b.book_id
                    LEFT JOIN 
                        Loans l ON lb.library_book_id = l.library_book_id
                    GROUP BY 
                        b.title
                    ORDER BY 
                        kiralanma_sayisi DESC
                """)
                
                sonuclar = cursor.fetchall()
                return jsonify({'kitap_durumu': [
                    {
                        'kitap_adi': sonuc[0],
                        'kiralanma_sayisi': sonuc[1],
                        'kiralanabilir_adet': sonuc[2]
                    } for sonuc in sonuclar
                ]})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002, debug=True)