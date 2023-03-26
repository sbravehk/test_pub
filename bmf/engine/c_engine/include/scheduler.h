/*
 * Copyright 2023 Babit Authors
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef BMF_SCHEDULER_H
#define BMF_SCHEDULER_H

#include<thread>
#include"scheduler_queue.h"
#include"node.h"

BEGIN_BMF_ENGINE_NS
    USE_BMF_SDK_NS

    class NodeItem {
    public:
        NodeItem(std::shared_ptr<Node> node = nullptr);

        std::shared_ptr<Node> node_;
        int64_t last_scheduled_time_;
        // TODO: Usage?
        int nodes_ref_cnt_;
    };

    class SchedulerCallBack {
    public:
        std::function<int(int, std::shared_ptr<Node> &)> get_node_;
    };

    class Scheduler {
    public:
        Scheduler(SchedulerCallBack callback, int scheduler_cnt = 1);

        int add_scheduler_queue();

        void pause();

        void resume();

        int start();

        int close();

        int add_or_remove_node(int node_id, bool is_add);

        bool choose_node_schedule(int64_t start_time, std::shared_ptr<Node> &node);

        int scheduling_thread();

        int schedule_node(Task &task);

        int clear_task(int node_id, int scheduler_queue_id);

        bool paused_ = false;
        std::vector<std::shared_ptr<SchedulerQueue> > scheduler_queues_;
        std::map<int, NodeItem> nodes_to_schedule_;
        std::thread exec_thread_;
        bool thread_quit_ = 0;
        std::recursive_mutex node_mutex_;
        std::exception_ptr eptr_;
        int64_t last_schedule_success_time_;
        SchedulerCallBack callback_;
    };

END_BMF_ENGINE_NS
#endif //BMF_SCHEDULER_H
