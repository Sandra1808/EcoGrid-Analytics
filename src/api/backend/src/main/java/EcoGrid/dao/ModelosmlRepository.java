package EcoGrid.dao;

import EcoGrid.entity.Modelosml;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface ModelosmlRepository extends JpaRepository<Modelosml, Long> {

    List<Modelosml> findByIndactivoTrueOrderByFecentrenamientoDesc();
}