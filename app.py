from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Enum, DateTime
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import enum
from datetime import datetime

# إعداد قاعدة البيانات المركزية
engine = create_engine('sqlite:///elite_team_system.db', echo=False)
Base = declarative_base()

# 1. تحديد مستويات الصلاحيات (التقسيم والإشراف)
class Role(enum.Enum):
    SUPER_ADMIN = "المدير العام" # صلاحيات مطلقة
    MANAGER = "رئيس قسم / مشرف" # صلاحيات إدارة المشاريع وتوزيع المهام
    MEMBER = "عضو فريق" # صلاحيات استلام وتحديث المهام فقط

# 2. تحديد حالات المهام
class TaskStatus(enum.Enum):
    PENDING = "لم يبدأ"
    IN_PROGRESS = "قيد العمل"
    COMPLETED = "مكتمل"

# ==========================================
# بناء الجداول (جداول المنظومة)
# ==========================================

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    role = Column(Enum(Role), nullable=False)
    department = Column(String)
    
    # علاقة المستخدم بالمهام المسندة إليه
    tasks = relationship("Task", back_populates="assignee")

class Project(Base):
    __tablename__ = 'projects'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    
    # علاقة المشروع بمهامه
    tasks = relationship("Task", back_populates="project")

class Task(Base):
    __tablename__ = 'tasks'
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    priority = Column(String) # عاجل، متوسط، عادي
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # ربط المهمة بالمشروع والمستخدم
    project_id = Column(Integer, ForeignKey('projects.id'))
    assignee_id = Column(Integer, ForeignKey('users.id'))
    
    project = relationship("Project", back_populates="tasks")
    assignee = relationship("User", back_populates="tasks")

# إنشاء الجداول في قاعدة البيانات
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# ==========================================
# دوال الإدارة والتشغيل (العمليات)
# ==========================================

def setup_system():
    """تهيئة النظام وإضافة أعضاء الفريق والمشاريع الأساسية"""
    # إضافة الأعضاء بالصلاحيات
    hammam = User(name="همَّام الكانمي", role=Role.SUPER_ADMIN, department="الإدارة العليا")
    sufyan = User(name="سفيان اليونسي", role=Role.MANAGER, department="إدارة المحتوى")
    abdulqader = User(name="عبد القادر مجيد", role=Role.MANAGER, department="التقنية والمنصات")
    nouha = User(name="نهى", role=Role.MEMBER, department="التنظيم والإدارة")
    
    # إضافة المشاريع
    bots = Project(name="بوتات زيد", description="إدارة وتحديث البوتات التعليمية")
    fadaa = Project(name="مشروع فضاء", description="منصة الفضاء التعليمية")
    manahil = Project(name="مناهل العلم", description="الامتحانات الإلكترونية")
    
    session.add_all([hammam, sufyan, abdulqader, nouha, bots, fadaa, manahil])
    session.commit()
    print("تمت تهيئة المنظومة بنجاح وإضافة الفريق والمشاريع!")

def assign_task(admin_name, task_title, project_name, assignee_name, priority):
    """دالة توزيع المهام (مربوطة بالصلاحيات)"""
    admin = session.query(User).filter_by(name=admin_name).first()
    
    # التحقق من الصلاحيات (فقط المدير أو المشرف يمكنه توزيع المهام)
    if admin.role in [Role.SUPER_ADMIN, Role.MANAGER]:
        project = session.query(Project).filter_by(name=project_name).first()
        assignee = session.query(User).filter_by(name=assignee_name).first()
        
        new_task = Task(title=task_title, project=project, assignee=assignee, priority=priority)
        session.add(new_task)
        session.commit()
        print(f"✅ تمت إضافة المهمة '{task_title}' بنجاح للمشروع '{project_name}' وإسنادها إلى '{assignee_name}'.")
    else:
        print("❌ عذراً، لا تملك الصلاحيات الكافية لتوزيع المهام.")

# ==========================================
# تشغيل وتجربة المنظومة
# ==========================================
if __name__ == "__main__":
    # 1. إعداد النظام
    setup_system()
    
    # 2. تجربة توزيع مهمة من قبل الإدارة
    assign_task(
        admin_name="همَّام الكانمي", 
        task_title="رفع امتحانات الشهر الجديد", 
        project_name="مناهل العلم", 
        assignee_name="سفيان اليونسي", 
        priority="عاجل"
    )
