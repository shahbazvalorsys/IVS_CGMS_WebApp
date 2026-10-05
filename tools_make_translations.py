"""Builds locale/ar/LC_MESSAGES/django.po and .mo from the table below.
Run:  python tools_make_translations.py
(On a machine with GNU gettext you can instead use: django-admin makemessages / compilemessages.)"""
import polib

T = {
 "Dashboard": "لوحة المعلومات", "Audit log": "سجل التدقيق", "Platform admin": "إدارة المنصة",
 "Password": "كلمة المرور", "Sign out": "تسجيل الخروج", "Sign in": "تسجيل الدخول",
 "Incorrect email or password, or the account is temporarily locked.": "البريد الإلكتروني أو كلمة المرور غير صحيحة، أو أن الحساب مقفل مؤقتًا.",
 "Email": "البريد الإلكتروني", "Change password": "تغيير كلمة المرور",
 "Use at least 10 characters. Avoid common passwords.": "استخدم 10 أحرف على الأقل وتجنب كلمات المرور الشائعة.",
 "Save password": "حفظ كلمة المرور",
 "Welcome to CGMS. Contracts, guarantees, cheques and alerts will appear here as each module is released.": "مرحبًا بك في نظام CGMS. ستظهر هنا العقود والضمانات والشيكات والتنبيهات مع إطلاق كل وحدة.",
 "Your role": "دورك", "Org Admin": "مدير النظام", "Company status": "حالة الشركة", "Release": "الإصدار",
 "Platform": "المنصة", "Client companies": "الشركات العملاء", "Company": "الشركة", "Status": "الحالة",
 "Created": "تاريخ الإنشاء", "No clients yet.": "لا توجد شركات بعد.",
 "Platform staff manage clients and subscriptions here. Client contract data is not visible to platform staff.": "يدير موظفو المنصة الشركات والاشتراكات هنا. بيانات عقود العملاء غير مرئية لموظفي المنصة.",
 "Access limited": "الوصول محدود", "Access is limited for this company": "الوصول إلى هذه الشركة محدود",
 "The subscription has ended and the company is in a grace period. You can view data but not change it. Please renew.": "انتهى الاشتراك والشركة في فترة سماح. يمكنك عرض البيانات ولكن لا يمكنك تعديلها. يرجى التجديد.",
 "This company\u2019s subscription is not active. Please contact your administrator or IVS.": "اشتراك هذه الشركة غير فعّال. يرجى التواصل مع مسؤول النظام أو IVS.",
 "All actions": "جميع الإجراءات", "Search record": "بحث في السجلات", "Filter": "تصفية", "When": "متى",
 "User": "المستخدم", "Action": "الإجراء", "Record": "السجل", "Changes": "التغييرات", "No entries.": "لا توجد قيود.",
 "Previous": "السابق", "Next": "التالي", "Trial": "تجريبي", "Active": "فعّال", "Grace": "فترة سماح",
 "Expired": "منتهي", "Suspended": "معلّق", "Closed": "مغلق", "Full": "كامل", "Viewer": "مشاهد",
}
po = polib.POFile()
po.metadata = {"Project-Id-Version": "CGMS 1.0", "Language": "ar", "MIME-Version": "1.0",
               "Content-Type": "text/plain; charset=UTF-8", "Content-Transfer-Encoding": "8bit",
               "Plural-Forms": "nplurals=6; plural=(n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 ? 4 : 5);"}
for k, v in T.items():
    po.append(polib.POEntry(msgid=k, msgstr=v))
po.save("locale/ar/LC_MESSAGES/django.po")
po.save_as_mofile("locale/ar/LC_MESSAGES/django.mo")
print(len(T), "strings written")
