package EcoGrid.dao;

import EcoGrid.entity.AlertasOperativa;
import org.springframework.data.jpa.repository.EntityGraph;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

import java.time.LocalDateTime;
import java.util.List;

public interface AlertasOperativaRepository
        extends JpaRepository<AlertasOperativa, Long> {

    @EntityGraph(attributePaths = "idtiempo")
    List<AlertasOperativa> findAllByOrderByIdtiempo_FechoraDesc();

    @EntityGraph(attributePaths = "idtiempo")
    List<AlertasOperativa> findByIdtiempo_FechoraBetweenOrderByIdtiempo_FechoraDesc(
            LocalDateTime desde, LocalDateTime hasta);

    @Query("""
            select count(a)
            from AlertasOperativa a
            where lower(a.estado) in ('activa', 'abierta', 'pendiente')
            """)
    long contarActivas();
}