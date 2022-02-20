import asyncio
import time
from copy import deepcopy

from sqlalchemy import select, and_, or_, null

from app.crud import Mapper
from app.handler.fatcory import PityResponse
from app.models import async_session, DatabaseHelper
from app.models.report import PityReport
from app.models.schema.test_plan import PityTestPlanForm
from app.models.test_plan import PityTestPlan
from app.models.testplan_follow_user import PityTestPlanFollowUserRel
from app.utils.decorator import dao
from app.utils.logger import Log
from config import Config


@dao(PityTestPlan, Log("PityTestPlanDao"))
class PityTestPlanDao(Mapper):

    @staticmethod
    async def list_test_plan(page: int, size: int, project_id: int = None, name: str = '', priority: str = '',
                             create_user: int = None, user_id: int = None, follow: bool = None):
        try:
            async with async_session() as session:
                conditions = [PityTestPlan.deleted_at == 0]
                DatabaseHelper.where(project_id, PityTestPlan.project_id == project_id, conditions) \
                    .where(name, PityTestPlan.name.like(f"%{name}%"), conditions) \
                    .where(priority, PityTestPlan.priority == priority, conditions) \
                    .where(create_user, PityTestPlan.create_user == create_user, conditions)
                if follow is None:
                    sql = select(PityTestPlan, PityTestPlanFollowUserRel.id) \
                        .outerjoin(PityTestPlanFollowUserRel,
                                   and_(
                                       PityTestPlanFollowUserRel.user_id == user_id,
                                       PityTestPlanFollowUserRel.deleted_at == 0,
                                       PityTestPlanFollowUserRel.plan_id == PityTestPlan.id)) \
                        .where(*conditions)
                elif follow:
                    sql = select(PityTestPlan, PityTestPlanFollowUserRel.id) \
                        .outerjoin(PityTestPlanFollowUserRel,
                                   PityTestPlanFollowUserRel.plan_id == PityTestPlan.id,
                                   ).where(
                        *conditions, PityTestPlanFollowUserRel.user_id == user_id,
                                     PityTestPlanFollowUserRel.deleted_at == 0)
                else:
                    sql = select(PityTestPlan, null().label('null_bar')) \
                        .outerjoin(PityTestPlanFollowUserRel,
                                   PityTestPlanFollowUserRel.plan_id == PityTestPlan.id).where(
                        *conditions, or_(PityTestPlanFollowUserRel.id == None,
                                         PityTestPlanFollowUserRel.deleted_at != 0))
                print(sql)
                result, total = await DatabaseHelper.pagination(page, size, session, sql, False)
                return result, total
        except Exception as e:
            PityTestPlanDao.log.error(f"获取测试计划失败: {str(e)}")
            raise Exception(f"获取测试计划失败: {str(e)}")

    @staticmethod
    async def insert_test_plan(plan: PityTestPlanForm, user: int) -> PityTestPlan:
        try:
            async with async_session() as session:
                async with session.begin():
                    query = await session.execute(select(PityTestPlan).where(PityTestPlan.project_id == plan.project_id,
                                                                             PityTestPlan.name == plan.name,
                                                                             PityTestPlan.deleted_at == 0))
                    if query.scalars().first() is not None:
                        raise Exception("测试计划已存在")
                    test_plan = PityTestPlan(**plan.dict(), user=user)
                    session.add(test_plan)
                    await session.flush()
                    await session.refresh(test_plan)
                    session.expunge(test_plan)
                    return test_plan
        except Exception as e:
            PityTestPlanDao.log.error(f"新增测试计划失败: {str(e)}")
            raise Exception(f"添加失败: {str(e)}")

    @classmethod
    async def update_test_plan(cls, plan: PityTestPlanForm, user: int, log=False):
        try:
            async with async_session() as session:
                async with session.begin():
                    query = await session.execute(
                        select(PityTestPlan).where(PityTestPlan.id == plan.id, PityTestPlan.deleted_at == 0))
                    data = query.scalars().first()
                    if data is None:
                        raise Exception("测试计划不存在")
                    old = deepcopy(data)
                    plan.env = ",".join(map(str, plan.env))
                    plan.receiver = ",".join(map(str, plan.receiver))
                    plan.case_list = ",".join(map(str, plan.case_list))
                    plan.msg_type = ",".join(map(str, plan.msg_type))
                    changed = DatabaseHelper.update_model(data, plan, user)
                    await session.flush()
                    session.expunge(data)
                if log:
                    async with session.begin():
                        await asyncio.create_task(
                            cls.insert_log(session, user, Config.OperationType.UPDATE, data, old, plan.id, changed))
        except Exception as e:
            PityTestPlanDao.log.error(f"编辑测试计划失败: {str(e)}")
            raise Exception(f"编辑失败: {str(e)}")

    @staticmethod
    async def update_test_plan_state(id: int, state: int):
        try:
            async with async_session() as session:
                async with session.begin():
                    query = await session.execute(
                        select(PityTestPlan).where(PityTestPlan.id == id, PityTestPlan.deleted_at == 0))
                    data = query.scalars().first()
                    if data is None:
                        raise Exception("测试计划不存在")
                    data.state = state
                    # await session.flush()
                    # session.expunge(data)
                    # return data
        except Exception as e:
            PityTestPlanDao.log.error(f"编辑测试计划失败: {str(e)}")
            raise Exception(f"编辑失败: {str(e)}")

    @staticmethod
    async def query_test_plan(id: int) -> PityTestPlan:
        try:
            async with async_session() as session:
                sql = select(PityTestPlan).where(PityTestPlan.deleted_at == 0, PityTestPlan.id == id)
                data = await session.execute(sql)
                return data.scalars().first()
        except Exception as e:
            PityTestPlanDao.log.error(f"获取测试计划失败: {str(e)}")
            raise Exception(f"获取测试计划失败: {str(e)}")

    # @staticmethod
    # async def delete_test_plan(id: int, user: int):
    #     try:
    #         async with async_session() as session:
    #             async with session.begin():
    #                 query = await session.execute(
    #                     select(PityTestPlan).where(PityTestPlan.id == id, PityTestPlan.deleted_at == 0))
    #                 data = query.scalars().first()
    #                 if data is None:
    #                     raise Exception("测试计划不存在")
    #                 DatabaseHelper.delete_model(data, user)
    #     except Exception as e:
    #         PityTestPlanDao.log.error(f"删除测试计划失败: {str(e)}")
    #         raise Exception(f"删除失败: {str(e)}")

    @staticmethod
    async def follow_test_plan(plan_id: int, user_id: int):
        """
        关注测试计划
        :param plan_id:
        :param user_id:
        :return:
        """
        async with async_session() as session:
            async with session.begin():
                sql = select(PityTestPlanFollowUserRel).where(PityTestPlanFollowUserRel.deleted_at == 0,
                                                              PityTestPlanFollowUserRel.plan_id == plan_id,
                                                              PityTestPlanFollowUserRel.user_id == user_id)
                data = await session.execute(sql)
                ans = data.scalars().first()
                if ans is not None:
                    raise Exception("已关注过此测试计划")
                model = PityTestPlanFollowUserRel(plan_id, user_id, user_id)
                session.add(model)

    @staticmethod
    async def unfollow_test_plan(plan_id: int, user_id: int):
        """
        取关测试计划
        :param plan_id:
        :param user_id:
        :return:
        """
        async with async_session() as session:
            async with session.begin():
                sql = select(PityTestPlanFollowUserRel).where(PityTestPlanFollowUserRel.deleted_at == 0,
                                                              PityTestPlanFollowUserRel.plan_id == plan_id,
                                                              PityTestPlanFollowUserRel.user_id == user_id)
                data = await session.execute(sql)
                ans = data.scalars().first()
                if ans is None:
                    raise Exception("已取关过此测试计划")
                ans.deleted_at = time.time_ns()

    @staticmethod
    async def query_user_follow_test_plan(user_id: int):
        """
        根据用户id查询出用户关注的测试计划执行数据
        :param user_id:
        :return:
        """
        ans = []
        async with async_session() as session:
            async with session.begin():
                # 找到最近7次通过率
                sql = select(PityReport, PityTestPlan).outerjoin(PityTestPlan, PityTestPlan.id == PityReport.plan_id) \
                    .outerjoin(PityTestPlanFollowUserRel, PityTestPlanFollowUserRel.plan_id == PityTestPlan.id) \
                    .where(PityTestPlanFollowUserRel.deleted_at == 0, PityTestPlanFollowUserRel.user_id == user_id) \
                    .order_by(PityReport.start_at.desc()).limit(7)
                data = await session.execute(sql)
                temp = dict()
                for items in data.all():
                    report, plan = items
                    if plan.id not in temp:
                        ans.append({
                            "plan": PityResponse.model_to_dict(plan),
                            "report": [],
                        })
                        temp[plan.id] = len(ans) - 1
                    ans[temp[plan.id]]["report"].append(PityResponse.model_to_dict(report))
        return ans
