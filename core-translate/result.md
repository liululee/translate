See Fescar source code is strenuous?See Fescar source code is strenuous?Let's take a look at this source code interpretation.See Fescar source code is strenuous?Let's take a look at this source code interpretation.



Normally, the isolation level of the database transaction is set to *read committed (* has met the business requirements, so the isolation level corresponding to the branch (local) transaction in Fescar is *read committed*).So what is the isolation level for global transactions in Fescar?If you have seen before [distributed transaction middleware Fescar-RM module source code interpretation] should be able to deduce: Fescar defines the default isolation for global transactions as *read uncommitted*.For the impact of *reading unsubmitted* isolation level on the business, I think everyone will be more clear, and will read dirty data. The classic example is bank transfer, and there is a problem of data inconsistency.For Fescar, if you don't take any other technical means, there will be serious problems, such as:


![img](https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YYkOuialG2pfnxHibicUjzdFV2RVgGxk6W4pGoELszDZmZ3icrKhZ9ofCnD4ARSB0e2YfzMuqlraQ/640?Wx_fmt=jpeg&tp=webp&wxfrom=5&wx_lazy=1&wx_co=1)
As shown in the figure above, ask which state should the global transaction A roll back to the resource R1?



Obviously, if you do a rollback according to UndoLog, a serious problem will occur: overwrite the change of resource R1 by global transaction B.How does Fescar solve this problem?The answer is Fescar's global write exclusive lock solution, in which global transaction B is in a wait state because global locks are not available.



For Fescar's isolation level, an official paragraph is quoted to illustrate:


> The isolation of global transactions is based on the local isolation level of branch transactions.
>>> At the database local isolation level Read committed or above, Fescar designed a global write exclusive lock maintained by the transaction coordinator to ensure write isolation between transactions, and global transactions are defined by default at the uncommitted isolation level.
> Our consensus on isolation levels is that most applications work without problems under the read isolation level.In fact, there are most of the application scenarios in this case. In fact, there is no problem in working under the uncommitted isolation level.
>>> In extreme scenarios, if the application needs to achieve a global read submission, Fescar also provides a mechanism to achieve the goal.By default, Fescar is working under the uncommitted isolation level to ensure the efficiency of most scenarios.



This article will go deep into the source layer to interpret Fescar's global write exclusive lock implementation.Fescar global write exclusive lock implementation is maintained in the TC (Transaction Coordinator) module, RM (Resource Manager) module will request the TC module in the place where the lock is required to obtain the global lock to ensure write isolation between transactions, the following is divided into two parts :TC - Global write exclusive lock implementation, RM - global write exclusive lock use.





**TC - Global write exclusive implementation **
------


First look at the entry of the TC module and the external interaction, the following figure is the main function of the TC module:


![img](https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YYkOuialG2pfnxHibicUjzYlFl4lPORHRm8d2Q927ca3dzP7ibd4uFZVtraRM5LSibExGvp1e8pChQ/640?Wx_fmt=jpeg&tp=webp&wxfrom=5&wx_lazy=1&wx_co=1)


The figure above shows that RpcServer handles the communication protocol related logic, and the real processor for the TC module is DefaultCoordiantor, which contains all the external exposed functions of the TC, such as doGlobalBegin (global transaction creation), doGlobalCommit (global transaction commit), doGlobalRollback (global Transaction rollback), doBranchReport (branch transaction status report), doBranchRegister (branch transaction registration), doLockCheck (global write exclusive lock check), etc., where doBranchRegister, doLockCheck, doGlobalCommit is the entry point for the global write exclusive lock implementation.



```/*** Branch transaction registration, will get the global lock resource of the branch transaction during the registration process */@Overrideprotected void doBranchRegister(BranchRegisterRequest request, BranchRegisterResponse response, RpcContext rpcContext) throws TransactionException { response.setTransactionId(request.getTransactionId()); response.setBranchId(core.branchRegister(request.getBranchType(), request.getResourceId(), rpcContext.getClientId(), XID.generateXID(request.getTransactionId()), request.getLockKey()));}/*** Check if the global lock can be obtained. */@Overrideprotected void doLockCheck(GlobalLockQueryRequest request, GlobalLockQueryResponse response, RpcContext rpcContext) throws TransactionException { response.setLockable(core.lockQuery(request.getBranchType(), request.getResourceId(), XID. generateXID(request.getTransactionId()), request.getLockKey()));}/*** Global transaction commit, will release the lock occupancy record of all branch transactions under the global transaction */@Overridepr Otected void doGlobalCommit(GlobalCommitRequest request, GlobalCommitResponse response, RpcContext rpcContext)throws TransactionException { response.setGlobalStatus(core.commit(XID.generateXID(request.getTransactionId())));}```
The above code logic will eventually be delegated to DefualtCore for execution.



![img](data:image/gif;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQImWNgYGBgAAAABQABh6FO1AAAAABJRU5ErkJggg==)


As shown above, whether it is the acquisition lock or the check lock state logic, it will eventually be taken over by LockManger, and the LockManager logic is implemented by DefaultLockManagerImpl. All designs with global write exclusive locks are maintained in DefaultLockManagerImpl.



First look at the structure of the global write exclusive lock:


```Private static final ConcurrentHashMap<String, ConcurrentHashMap<String, ConcurrentHashMap<Integer, Map<String, Long>>>> LOCK_MAP = new ConcurrentHashMap<~>();```


![img](https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YYkOuialG2pfnxHibicUjzLuEvypJlfDdoxWDZtQlNxPRxGeJIc1DqjMdY8OcCHfenR49wkxKe4g/640?Wx_fmt=jpeg&tp=webp&wxfrom=5&wx_lazy=1&wx_co=1)


Overall, the lock structure is designed using Map. The first half uses ConcurrentHashMap, and the second half uses HashMap. In the end, it is actually a lock occupancy mark: corresponding to a primary key in a Tabel on a ResourceId (database source ID). The global write exclusive of the row record is occupied by which global transaction.Below, let's take a look at the source code for the specific lock:
![img](https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YYkOuialG2pfnxHibicUjzpI2WaPU9dqne2nVSpCJyWWOWt4VtAJktkmYMlVmYB25njEOohImFcw/640?Wx_fmt=jpeg&tp=webp&wxfrom=5&wx_lazy=1&wx_co=1)
As noted in the above figure, the entire acquireLock logic is still very clear. For the lock resources required for branch transactions, either the ones are successfully acquired all at once, or all fail, and there is no partial success.Through the above explanation, there may be two questions:


1. Why does the first half of the lock structure use ConcurrentHashMap and the second half uses HashMap?

> The first half uses ConcurrentHashMap to understand: In order to support better concurrent processing; the question is why the second half does not directly use ConcurrentHashMap, but use HashMap?The possible reason is because the latter part needs to determine whether the current global transaction occupies the lock resource corresponding to the PK. It is a compound operation. Even if ConcurrentHashMap is used, it is not necessary to use Synchronized lock to judge. It is better to use a more lightweight one. HashMap.



2. Why does the BranchSession store the lock resources it holds?

> This is relatively simple, in the structure of the entire lock does not reflect the lock records occupied by the branch transaction, so if the global transaction commit, how to release the lock resources occupied by the branch transaction?So the BranchSession saves the lock resources occupied by the branch transactions.



The following figure shows how the validation global lock resource can be fetched:
![img](data:image/gif;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQImWNgYGBgAAAABQABh6FO1AAAAABJRU5ErkJggg==)


The following figure shows the branch transaction release global lock resource logic:
![img](https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YYkOuialG2pfnxHibicUjz1MRCI1kibC8WDbIFPpk48LP1UdMQqibAjun0ibj18r3lkhPeIj3Jr61KQ/640?Wx_fmt=jpeg&tp=webp&wxfrom=5&wx_lazy=1&wx_co=1)


The above is the implementation principle of the global write exclusive lock in the TC module: when the branch transaction is registered, the RM will pass the lock resources required by the current branch office together, and the TC obtains the global lock resource acquisition (either one time all succeeds). , or all fail, there is no partial success failure; when the global transaction commits, the TC module automatically releases the lock resources held by all branch transactions under the global transaction; meanwhile, the probability of failure is obtained to reduce the global write exclusive lock. The TC module exposes whether the check lock resource can be acquired, and the RM module can be verified at the appropriate location to reduce the probability of failure when the branch transaction is registered.





**RM - global write exclusive use **
------


In the RM module, the two functions of the global lock of the TC module are mainly used. One is to check whether the global lock can be acquired, the other is to register the branch transaction to occupy the global lock, and the global lock release is independent of the RM, and the TC module is global. Automatically released when the transaction commits.Before the branch transaction is registered, the global lock state check logic is performed to ensure that the lock registration does not occur in the branch registration.



When executing the Update, Insert, and Delete statements, data snapshots are generated before and after sql execution to organize into UndoLog. The way to generate snapshots is basically in the form of Select...For Update. RM tries to check whether the global lock can be verified. The acquired logic is in the executor that executes the statement: SelectForUpdateExecutor, as shown below:
![img](https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YYkOuialG2pfnxHibicUjzkXehmV3vOqFPicQJQMePcicicSOloc8UhM1nRpzMNSibaEPk8AXjhib7tnw/640?Wx_fmt=jpeg&tp=webp&wxfrom=5&wx_lazy=1&wx_co=1)
![img](https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YYkOuialG2pfnxHibicUjzWnickAibsXme3jiaFKK34icaDpialEQW9mWPPMkwkSZqKPLMzFKKyxO3sVQ/640?Wx_fmt=jpeg&tp=webp&wxfrom=5&wx_lazy=1&wx_co=1)


The basic logic is as follows:
A. Execute the Select ... For update statement, so that the local transaction occupies the corresponding row lock of the database. Other local transactions cannot seize the local database row lock, and thus will not preempt the global lock.



B. Loop to know whether the global lock can be obtained, because the global lock may be obtained before the current global transaction, so you need to wait for the previous global transaction to release the global lock resource; if the check can get the global lock, then Due to the reason of step 1, other local transactions will not acquire the global lock before the current local transaction ends, thus ensuring that the branch transaction registration before the current local transaction commit will not fail due to the global lock conflict.



Note: Careful students may find that for the UpdateExecutor and DeleteExecutor corresponding to the Update and Delete statements, the Select..For Update statement will be executed to obtain the beforeImage, and then the global lock resource state will be verified, and the InsertExecutor corresponding to the Insert statement will be verified. There is no relevant global lock check logic. The reason may be: because it is Insert, the corresponding insert row PK is new, the global lock resource must be unoccupied, and then the global lock corresponding to the branch transaction registration before the local transaction commit Resources must be available.



Next, let's take a look at how the branch transaction is committed, how to generate and save the global lock resources that need to be occupied in the branch transaction.First, after executing SQL to complete the business SQL, UndoLog will be generated according to beforeImage and afterImage. At the same time, the global lock resource identifier that the current local office needs to occupy will also be generated and stored in the ConnectionContext of ContentoionProxy, as shown in the following figure:
![img](https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YYkOuialG2pfnxHibicUjzcfvicWLu0IdnIfGHGbNx5RGhwkKicQCnb2OsVUgbGtDVO85n8awShvibw/640?Wx_fmt=jpeg&tp=webp&wxfrom=5&wx_lazy=1&wx_co=1)
![img](https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YYkOuialG2pfnxHibicUjzhZt1Lt5kTLmnpZurYUUNvW9rRTJEq0rzIJCMg0GjfE6x1TKpiaPwxyw/640?Wx_fmt=jpeg&tp=webp&wxfrom=5&wx_lazy=1&wx_co=1)


In ContentoionProxy.commit, when the branch transaction is registered, the global lock identifier saved in the context in the ConnectionProxy is passed to the TC for global lock acquisition.

![img](https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YYkOuialG2pfnxHibicUjzw6tlpPPOIQJCf0hcaLQbB622Dw2UpibfzdtorVy7dR7KFZEicFOB7ib5w/640?Wx_fmt=jpeg&tp=webp&wxfrom=5&wx_lazy=1&wx_co=1)


The above is the use logic of the global write exclusive lock in the RM module, because the global lock resource state will be checked cyclically before the real execution of the global lock resource is obtained, so that the lock conflict will not be defeated when the lock resource is actually acquired. But in fact, the disadvantage is also obvious: when the lock conflict is more serious, it will increase the length of the local transaction database lock, which will bring a certain performance loss to the service interface.





**to sum up**
------


This article details the global write exclusive lock that Fescar implements to achieve write isolation under the uncommitted isolation level, including the implementation principle of the global write exclusive lock in the TC module and how to write the global exclusive lock in the RM module. Use logic.In the process of understanding the source code, the author also left two problems:


A. The global write exclusive lock data structure is stored in the memory. What if the server is restarted/down? What is the high availability scheme of the TC module?

B. What happens to a lock conflict between a global transaction managed by Fescar and a local transaction managed by Fescar?The specific problem is as shown in the figure below. The question is: How does global transaction A roll back?



![img](https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YYkOuialG2pfnxHibicUjzjAfCVARyE1iaI3TLMyBf0MxT05OibQQqLAuAzusjIOD8jrC3yViaxYgHw/640?Wx_fmt=jpeg&tp=webp&wxfrom=5&wx_lazy=1&wx_co=1)
For Question 1, it is necessary to continue research; for Question 2, there is already an answer, but Fescar is currently not implemented. Specifically, the global transaction A will report an error when it rolls back. The branch transaction A1 in the global transaction A will check afterImage and current when it rolls back. Whether the corresponding row data in the table is consistent. If the data is consistent, the rollback is allowed. If the data is inconsistent, the rollback fails and the corresponding service party is notified by the alarm. The service party processes it.HelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloHelloWatching Fescar source code is hard?Take a look at this source code interpretation.Watching Fescar source code is hard?Take a look at this source code interpretation.Watching Fescar source code is hard?Take a look at this source code interpretation.Watching Fescar source code is hard?Take a look at this source code interpretation.



Normally, the isolation level of database transactions is set to * Read submitted (* satisfies business requirements, so the isolation level for branch (local) transactions in Fescar is * Read submitted *).So what is the isolation level for global transactions in Fescar?If you've seen [Source Code Interpretation of Fescar-RM Module in Distributed Transaction Middleware] (http://mp.weixin.qq.com/s?_ Students of Biz = MzU4NzU0MDIzOQ==&mid=2247485621&idx=3&sn=2ae44bb05555f1911250ba92b4692515&chksm=fdeb3ad5ca9c3c3e7998ff1baef9c8bbaf769bf514426dc383fcc921ad4b7e43b4497f&scene=21 wechat_rectscar) should be able to infer that the default definition of Fescar is read as * uncommitted.As for the impact of * uncommitted * isolation level on business, it must be clear to everyone that dirty data can be read. The classic example is bank transfer, which results in inconsistent data.For Fescar, if no other technical means are adopted, serious problems will arise, such as:


[img] (https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YkOuialG2pfnx HibicUjzdFV2Rgxk6W4pELszDZmZ3rKhZ9CnD4ARSB0e2YfzMuqraQ/640?Wx_fmt = JPEG & TP = webp & wxfrom = 5 & wx_lazy = 1 & wx_co = 1)
As shown in the figure above, what state should ultimately global transaction A roll back to resource R1?



Obviously, if you roll back based on UndoLog, a serious problem will occur: the change of resource R1 that covers global transaction B.So how does Fescar solve this problem?The answer is Fescar's Global Write Exclusive Lock Solution, in which Global Transaction B is in a waiting state because it can't get the Global Lock during the execution of Global Transaction A.



For the isolation level of Fescar, an official paragraph is quoted to illustrate:


> The isolation of global transactions is based on the local isolation level of branch transactions.
>>> On the premise that the database local isolation level read has been submitted or above, Fescar designed a global write exclusive lock maintained by transaction coordinator to ensure write isolation between transactions, and defined the global transaction by default on the read uncommitted isolation level.
> Our consensus on isolation levels is that it is not a problem for most applications to read submitted isolation levels.In fact, the vast majority of these application scenarios, in fact, work in the read uncommitted isolation level is no problem.
>>> In extreme scenarios, if the application needs to achieve global read submission, Fescar also provides the corresponding mechanism to achieve the goal.By default, Fescar works at the read uncommitted isolation level to ensure the efficiency of most scenarios.



This paper will go deep into the source code level to interpret the Fescar global write exclusive lock implementation scheme.Fescar global write exclusive lock implementation scheme is maintained in TC (Transaction Coordinator) module. RM (Resource Manager) module requests TC module where locks are needed to acquire global locks to ensure write isolation between transactions. The following two parts are introduced: TC - global write exclusive lock implementation scheme and RM - global write exclusive lock enabler. Use.





** TC - Global Write Exclusive Implementation Scheme**
---


First, look at the entrance of TC module and external interaction. The following figure is the main function of TC module:


[img] (https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YkOuialG2pfnxHibicUjzYlFl4lPORHRm8d2Q927ca3dzP7ibd4uFZVtraRM5LSibGvp1e8pChQ/640?Wx_fmt = JPEG & TP = webp & wxfrom = 5 & wx_lazy = 1 & wx_co = 1)


As can be seen from the figure above, Rpc Server handles communication protocol-related logic, while the real processor for TC module is Default Coordiantor, which contains all TC exposed functions, such as doGlobal Begin (global transaction creation), doGlobal Commit (global transaction submission), global Rollback (global transaction rollback), doBranchR. Eport (branch transaction status report), doBranch Register (branch transaction registration), doLockCheck (global write exclusive lock check) and so on, in which doBranchRegister, doLockCheck, doGlobalCommit are the entrance to the global write exclusive lock implementation scheme.



` ` ` `/ *** Branch transaction registration, in the registration process will obtain the global lock resource of branch transaction */@Overrideprotected void do Branch Register (Branch Register Request request, Branch Register Response response, RpcContext rpcContext), throws TransactionException {response.setTransactio) NId (request. getTransactionId ()); response. setBranchId (core. branchRegister (request. getBranchType (), request. getResourceId (), rpcContext. getClientId (), XID. eXID (request. getTransactionId ()), request. getLockKey ();}/*** Check whether the global lock can be obtained */@Overrideid LockCheck (Global LockQuery Request request, Global LockQuery Response response, RpcContext rpcContext) throws TransactionException {response.setLockable (core.lockQuery (request.getBranchType (), request.getResourceId (), XID (request.getTransactionId (), request.getLockKey ();}/* ** Global transaction submission releases */@Overrideprotected void doGlobalCommit (Global CommitRequest request, Global CommitResponse response, RpcContext rpcContext) throws TransactionException {response.setGlobalStatus (core.commit (XID.generateXID) (r) Equest.getTransactionId();}` ` ` `
The above code logic is eventually delegated to DefualtCore for execution.



[img] (data: image / gif; base64, iVBORw0KGgoAAAANSUhEUgAAAAAAAAAAAAAAAAAAAAAAAFFcSJAAAADUlEQVQImWNgAABQABh6FO1AAABJRU5kJgg=)


As shown above, whether acquiring locks or verifying lock state logic, will eventually be taken over by LockManger, while LockManager logic is implemented by DefaultLockManagerImpl, and all design and global write exclusive locks are maintained in DefaultLockManagerImpl.



Let's first look at the structure of global write exclusive locks:


` ` ` `Private static final Concurrent HashMap < String, Concurrent HashMap < String, Concurrent HashMap < Integer, Map < String, Long > LOCK_MAP = new Concurrent HashMap <~> ();` ` ` `


[img] (https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YkOuialG2pfnx HibicUjz LuEvypJlfDdoxWDZtQlNxPRxGeJIc1DqjMdY8 OcfenR49wkx4g/640?Wx_fmt = JPEG & TP = webp & wxfrom = 5 & wx_lazy = 1 & wx_co = 1)


As a whole, the lock structure is designed with Map. The first half uses Concurrent HashMap and the second half uses HashMap. In fact, the final part is a lock occupancy tag: which global transaction occupies the global write exclusion lock of the row record corresponding to a primary key in a Tabel on a ResourceId (database source ID).Next, let's look at the source code for obtaining the lock.
[img] (https://mmbiz.qpic.cn/mmbiz_jpg/qdzBE73hWsic7YkOuialG2pfnxHibicUjzpI2WaPU9dqne2nVSpCJyWWt4VtAJktkmYMlVmB25njEOOOOOOOOOOOOOOOOOOOImcw/640?Wx_fmt = JPEG & TP = webp & wxfrom = 5 & wx_lazy = 1 & wx_co = 1)
As noted in the above figure, the entire acquireLock logic is clear. For the lock resources required by the branch transaction, either all are successfully acquired at one time or all fail, and there is no partial success or partial failure.From the above explanation, there may be two questions:


1. Why is Concurrent HashMap used in the first half of the lock structure and HashMap used in the second half?

> The first half uses Concurrent HashMap to understand: in order to support better concurrency processing; the question is why the second half does not use Concurrent HashMap directly, but HashMap?The reason may be that the latter part needs to judge whether the current global transaction occupies the lock resources corresponding to PK. It is a composite operation. Even if Concurrent HashMap is used, it is unavoidable to use Synchronized lock to judge. It is better to use lighter HashMap directly.



2. Why does BranchSession store lock resources held?

> This is relatively simple, which lock records are occupied by branch transactions in the whole lock structure, so how can branch transactions release the lock resources occupied when global transactions are committed?So the lock resources occupied by branch transactions are saved in BranchSession.



The following figure shows the logic for verifying whether global lock resources can be acquired:
[img] (data: image / gif; base64, iVBORw0KGgoAAAANSUhEUgAAAAAAAAAAAAAAAAAAAAAAAFFcSJAAAADUlEQVQImWNgAABQABh6FO1AAABJRU5kJgg=)


The following figure shows the branch transaction release global lock resource logic:
[img] (https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YkOuialG2pfnxHibicUjz1MRCI1kibC8WDbIFPk48LP1UdMQqibAjun0j18r3lkhIj3Jr61KQ/640?Wx_fmt = JPEG & TP = webp & wxfrom = 5 & wx_lazy = 1 & wx_co = 1)


The above is the implementation principle of global write exclusive lock in TC module: RM will transfer the lock resources needed by current branch firms when registering branch transactions, TC acquisition is responsible for the acquisition of global lock resources (either one-time all success, or all failure, there is no part of success failure); in the global event, RM is responsible for the acquisition of global lock resources. TC module automatically releases lock resources held by all branch transactions under global transaction when transaction commits; meanwhile, in order to reduce the failure probability of global write exclusive lock acquisition, TC module exposes whether the check lock resources can be acquired interface, RM module can verify them in appropriate location to reduce the registration of branch transactions. Failure probability.





** RM - Global Writing Exclusive Trivial Use**
---


In RM module, two functions of TC module global lock are mainly used. One is to check whether the global lock can be acquired. The other is to register branch transactions to occupy the global lock. The release of global lock is independent of RM, and is automatically released by TC module when the global transaction is submitted.Before branch transaction registration, the global lock state checking logic is used to ensure that branch registration does not have lock conflicts.



When executing Update, Insert, Delete statements, data snapshots are generated before and after SQL execution to organize into UndoLog, and snapshots are basically generated in the form of Select... For Update. RM tries to verify whether global locks can be acquired by the logic in the execution of the statement: Select Fordate Executor. The figure is as follows:
[img] (https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YkOuialG2pfnxHibicUjzkXehmV3vOqFPicQPcicSO8UhM1nRpzMNSibak8AXhib7tnw/640?Wx_fmt = JPEG & TP = webp & wxfrom = 5 & wx_lazy = 1 & wx_co = 1)
[img] (https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YkOuialG2pfnxHibicUjzWnickAisXme3jiaFKK34icaalDpialQEW9mWPPMkwSZqKPLMzKFKxO3sVQ/640?Wx_fmt = JPEG & TP = webp & wxfrom = 5 & wx_lazy = 1 & wx_co = 1)


The basic logic is as follows:
A. Execute the Select... For UPDATE statement so that the local transaction occupies the corresponding row lock of the database, and other local transactions will not preempt the global lock because they cannot preempt the row lock of the local database.



B. Cyclic control verifies that global locks can be acquired, because global locks may be acquired prior to the current global transaction, it is necessary to wait for the previous global transaction to release the global lock resources; if global locks can be acquired here, then due to Step 1, before the current local transaction ends, other local transactions are It does not acquire global locks, thus ensuring that branch transaction registration before the current local transaction submission does not fail due to global lock conflicts.



Note: Careful students may find that for Update and Delete statements, Update Executor and Delete Executor will execute Select.. For Update statement because of acquiring beforeImage, and then check the status of global lock resources. For Insert statement, Insert Executor has no relevant global lock verification logic. Perhaps: Because it is Insert, the corresponding insertion row PK is new, and the global lock resource must not be occupied, and then the corresponding global lock resource can be acquired when the branch transaction registers before the local transaction commits.



Next, let's look at how branch transactions are committed and how global lock resources that need to be occupied in branch transactions are generated and saved.Firstly, after the execution of business SQL, UndoLog is generated according to beforeImage and afterImage. At the same time, the global lock resource identification required by current local firms will be generated together and stored in the Connection Context of ContentoionProxy, as shown in the following figure:
[img] (https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YkOuialG2pnxHibicUjzcfvicWLu0IdnIfGHGbNx5RGhwkcQCnb2OsVUgbGtDVO85n8Ahvibw/640?Wx_fmt = JPEG & TP = webp & wxfrom = 5 & wx_lazy = 1 & wx_co = 1)
[img] (https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YkOuialG2pfnxHibicUjzhzt1Lt5kTLmnpZurYUUNvW9rJEq0rZMg0GjfE6x1TKpiaPwxyw/640?Wx_fmt = JPEG & TP = webp & wxfrom = 5 & wx_lazy = 1 & wx_co = 1)


In ContentoionProxy. commit, when branch transactions are registered, the global lock identity saved in context of ConnectionProxy is passed to TC for acquisition of global locks.

[img] (https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YkOuialG2pfnxHibicUjzw6tlpPPOIQJCf0hcaLQb622Dw2UpfztorVy7dR7KFZEicFOB7ib5w/640?Wx_fmt = JPEG & TP = webp & wxfrom = 5 & wx_lazy = 1 & wx_co = 1)


The above is the logic of using global write exclusive locks in RM module, because the state of global lock resources will be checked circularly before the acquisition of global lock resources is really carried out, so that the failure of acquiring lock resources will not be caused by lock conflicts in practice, but the disadvantages are also obvious: when lock conflicts are serious, local events will increase. The lock of transaction database takes a long time, which brings a certain performance loss to the business interface.





** Summary**
---


This paper describes in detail the global write exclusive lock implemented by Fescar to achieve write isolation at the read-uncommitted isolation level, including the implementation principle of the global write exclusive lock in TC module and the logic of how to use the global write exclusive lock in RM module.In the process of understanding the source code, the author also left two questions:


A. Global Write Exclusive Lock data structure is stored in memory. What if the server restarts/crashes? What is the high availability scheme of TC module?

B. What about lock conflicts between a Fescar-managed global transaction and a non-Fescar-managed local transaction?The specific problem is as follows: How does global transaction A roll back?



[img] (https://mmbiz.qpic.cn/mmbiz_jpg/qdzBE73hWsic7YkOuialG2pnx HibicUjzjAfCVARyE1iaI3TLMyBf0MxT05OQQLAuAzusjIOD8jrC3yViaxygHw/640?Wx_fmt = JPEG & TP = webp & wxfrom = 5 & wx_lazy = 1 & wx_co = 1)
Question 1 needs to be further studied; Question 2 has been answered, but Fescar is not yet implemented. Specifically, when global transaction A rolls back, it will report errors. When branch transaction A1 rolls back in global transaction A, it will check whether afterImage is consistent with the corresponding row data in the current table. If it is consistent, rollback will be allowed, and inconsistency will be rolled back. Failure and alarm to notify the corresponding business party, the business party shall handle it by itself.Watching Fescar source code is hard?Take a look at this source code interpretation.



Normally, the isolation level of database transactions is set to * Read submitted (* satisfies business requirements, so the isolation level for branch (local) transactions in Fescar is * Read submitted *).So what is the isolation level for global transactions in Fescar?If you've seen [Source Code Interpretation of Fescar-RM Module in Distributed Transaction Middleware] (http://mp.weixin.qq.com/s?_ Students of Biz = MzU4NzU0MDIzOQ==&mid=2247485621&idx=3&sn=2ae44bb05555f1911250ba92b4692515&chksm=fdeb3ad5ca9c3c3e7998ff1baef9c8bbaf769bf514426dc383fcc921ad4b7e43b4497f&scene=21 wechat_rectscar) should be able to infer that the default definition of Fescar is read as * uncommitted.As for the impact of * uncommitted * isolation level on business, it must be clear to everyone that dirty data can be read. The classic example is bank transfer, which results in inconsistent data.For Fescar, if no other technical means are adopted, serious problems will arise, such as:


[img] (https://mmbiz.qpic.cn/mmbiz_jpg/qdzZBE73hWsic7YkOuialG2pfnx HibicUjzdFV2Rgxk6W4pELszDZmZ3rKhZ9CnD4ARSB0e2YfzMuqraQ/640?Wx_fmt = JPEG & TP = webp & wxfrom = 5 & wx_lazy = 1 & wx_co = 1)
As shown in the figure above, what state should ultimately global transaction A roll back to resource R1?



Obviously, if you roll back based on UndoLog, a serious problem will occur: the change of resource R1 that covers global transaction B.So how does Fescar solve this problem?The answer is Fescar's Global Write Exclusive Lock Solution, in which Global Transaction B is in a waiting state because it can't get the Global Lock during the execution of Global Transaction A.



For the isolation level of Fescar, an official paragraph is quoted to illustrate:


> The isolation of global transactions is based on the local isolation level of branch transactions.
>>> On the premise that the database local isolation level read has been submitted or above, Fescar designed a global write exclusive lock maintained by transaction coordinator to ensure write isolation between transactions, and defined the global transaction by default on the read uncommitted isolation level.
